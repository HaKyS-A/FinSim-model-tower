""" 实现火山引擎大模型chat接口，同步 """
import asyncio
import os
import time
import logging
from volcenginesdkarkruntime import AsyncArk,Ark
import traceback
try:
    from . import global_variables
except:
    import global_variables

VOLC_KEY_PATH = 'volc_key.txt'

# 获取当前程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))
# 从文件读取 api key
try:
    with open(os.path.join(current_path, VOLC_KEY_PATH), 'r', encoding='utf-8') as f:
        VOLC_KEY = f.read().strip()
except Exception as e:
    raise ValueError(f'volc_engine api key does not exist - {VOLC_KEY_PATH} - {e}')

class ChatBasicVolc:
    """
    火山引擎大语言模型chat接口调用，同步
    """
    def __init__(self, model='deepseek-v3-250324', context=None, temperature=0.85, top_p=0.95, max_tokens=8192, thinking: str ='disabled'):
        """
        初始化函数，
        :param model: 模型id，从官网获取， https://www.volcengine.com/docs/82379/1513689
        :param context: 上下文，常规格式 system + (user -> assistant)
        :param temperature: 温度
        :param top_p: top_p
        :param max_tokens: 最大生成token数
        :param thinking: 是否限制模型思考,默认为‘auto’，模型自行选择
        """
        self.model = model
        if context is None:
            self.context = []
        else:
            self.context = context
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens=max_tokens
        self.thinking = thinking
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.client=Ark(api_key=VOLC_KEY)

    def get_usage(self):
        """ return tokens usage - (prompt, completion)"""
        return self.prompt_tokens, self.completion_tokens
    
    def append_context(self, content, role='user'):
        """
        添加聊天上下文，默认为添加用户提示词；每次LLM做出响应的时候同样需要添加至上下文；
        在智能体初始化阶段，可以设定 role 为 ‘system’，以添加系统人设
        :param content: 新增的对话内容
        :param role: 对话角色 system-人设；user-用户；assistant-模型
        :return: 新内容字典
        """
        self.context.append({'role': role, 'content': content})
        return {'role': role, 'content': content}
    
    def remove_context(self, beginning, ending=None):
        """
        删除对话上下文，从 begin 开始， end 结束， 均为 idx
        :param beginning: 开始 idx ， role 必须为 user，可以（通常）为负数
        :param ending: 结束 idx，默认为最后一句， role 必须为 assistant
        :return: 删除的全部内容
        """
        if ending is None:
            ending = len(self.context)

        # 确认删除内容合法，不会导致上下文角色错误
        assert (self.context[beginning]['role'] == 'user'), f"起始对话角色不为user: {beginning}, {self.context[beginning]}"
        assert (self.context[ending-1]['role'] == 'assistant'), f"终止对话角色不为assistant: {ending-1}, {self.context[ending-1]}"

        del_lst = self.context[beginning:ending]
        del self.context[beginning:ending]
        return del_lst

    def chat_basic(self, prompt):
        """
        以当前的对话上下文和参数进行一轮对话，会自动将模型回复加入上下文
        :param prompt: 该轮对话的提示词
        :return: LLM 的输出(dict{'role', 'content'})
        """
        self.append_context(prompt)
        for i in range(5):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.context,
                    stream=False,
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    temperature=self.temperature,
                    thinking={
                        "type": "disabled", # 不使用深度思考能力
                        # "type": "enabled", # 使用深度思考能力
                        # "type": "auto", # 模型自行判断是否使用深度思考能力
                    }
                )
                self.prompt_tokens += response.usage.prompt_tokens
                self.completion_tokens += response.usage.completion_tokens
                global_variables.Prompt_Usage+=response.usage.prompt_tokens
                global_variables.Completion_Usage+=response.usage.completion_tokens
                break
            except:
                # 请求失败
                time.sleep(0.5+5*i*i)
                print(f'\n-----请求失败{i+1}, sleep-{i}-----')
        else:
            print('\n-----重试5次仍然失败-----\n 退出')
            print('\n', self.context)
            raise TimeoutError('Deepseek API 出错')

        return self.append_context(response.choices[0].message.content, role='assistant')
        
    def chat_basic_temp(self, pop_fn, check_fn, **kwargs) -> int | list:
        """
        以当前的对话上下文和参数进行一轮对话，会自动将模型回复加入上下文
        :param prompt: 该轮对话的提示词
        :return: LLM 的输出(dict{'role', 'content'})
        """
        output = []
        print('-' * 40)

        n=0
        while True:
            prompt_tuple = pop_fn(n, **kwargs)  # self.context update——dynamic n
            prompt = prompt_tuple[0]
            if prompt == '':
                # no more prompts in prompt series
                return output
            
            retry = 0   # a variable to judge error

            while True:
                try:
                    # LLM generation
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=self.context,
                        stream=False,
                        max_tokens=self.max_tokens,
                        top_p=self.top_p,
                        temperature=self.temperature,
                        thinking={
                            "type": "disabled", # 不使用深度思考能力
                            # "type": "enabled", # 使用深度思考能力
                            # "type": "auto", # 模型自行判断是否使用深度思考能力
                        }
                    )
                    self.prompt_tokens += response.usage.prompt_tokens
                    self.completion_tokens += response.usage.completion_tokens
                    global_variables.Prompt_Usage+=response.usage.prompt_tokens
                    global_variables.Completion_Usage+=response.usage.completion_tokens

                    answer=response.choices[0].message.content

                    # response check
                    valid, data = check_fn(answer, n)
                    if valid:
                        # pass the check
                        if data:
                            # exist output data
                            output.append(data)
                        n += 1
                        del response
                        del answer
                        break

                    # fail to pass the check
                    retry += 1
                    if retry > 5:
                        raise ValueError('Cannot generate valid output in 5 times. -00')
                    del response, answer
                except ValueError:
                    # data format error in generation
                    if retry > 5:
                        print('Cannot generate valid output in 5 times. -01')
                        return -1
                    retry += 1
                    print('LLM error')
                except Exception:
                    # Cloud service errors or other errors
                    traceback.print_exc()
                    if retry > 10:
                        print('Cloud service error')
                        return -1
                    retry += 1
                    print('Cloud service error')

def test_pop_fn(n):
    if n == 0:
        return ['这是一条测试']
    else:
        return ['']


def test_check_fn(content, n):
    print(content)
    return True, None


if __name__ == '__main__':
    test = ChatBasicVolc(model='deepseek-v3-250324',
        context=[{'role': 'user', 'content': '测试'}],
        temperature=0.85,top_p=0.95
    )
    a=test.chat_basic("请和我说你好")
    print(a)