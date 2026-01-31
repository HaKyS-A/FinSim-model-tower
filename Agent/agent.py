"""所有智能体类的定义与"""
try:
    from .chat_volc import ChatBasicVolc
except:
    from chat_volc import ChatBasicVolc
import os

# 获取当前主程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))

class AgentBasic:
    """
    智能体基类，只保留所有智能体的最基础功能
    """

    def __init__(self, profile, model_name="deepseek-v3-2-251201", temperature=0.6, top_p=0.9, log_file='log.out'):
        """
        初始化函数
        :param model_name: 模型名称
        :param profile: 系统人设
        :param temperature: 温度参数，默认 0.6
        :param top_p: top_p 参数，默认0.9
        :param log_file: 日志文件，默认路径 "log,out"
        """
        self.chat = ChatBasicVolc(
            model=model_name,
            context=[],
            temperature=temperature,
            top_p=top_p
        )
        self.profile = profile
        self.chat.append_context(profile, role='system')
        self.log_file = os.path.join(current_path, log_file)
        folder=os.path.dirname(self.log_file)
        os.makedirs(folder,exist_ok=True)

    def get_befores(self):
        """ return before - [before_long, before_short, before_before_long, before_before_short]"""
        return (self.before_long, self.before_short, self.before_before_long, self.before_before_short)

    def get_usage(self):
        """ return tokens usage - (prompt, completion)"""
        return self.chat.get_usage()

    def get_profile(self):
        """ return self.profile """
        return self.profile

    def chat_with_log(self, prompt, to_print=False):
        """
        进行一轮对话并将内容存储至日志文件
        :param prompt: 提示词
        :return: 对话字典
        """
        response = self.chat.chat_basic(prompt=prompt)
        with open(os.path.join(current_path, self.log_file), 'a', encoding='utf-8') as f:
            f.write(
                '--**--\n{role:s}: {content:s}\n'.format(
                    role='user',
                    content=prompt
                )
            )
            f.write(
                '{role:s}: {content:s}\n--**--\n'.format(
                    role=response['role'],
                    content=response['content']
                )
            )
            if to_print:
                print(response)
            return response

    def system_broadcast(self, message, response='好的，我明白了。'):
        """
        系统广播方法，添加一轮对话并确认
        :param message: 广播内容
        :param response: 智能体被动回复，默认为 ”好的，我明白了。“
        :return: 广播是否成功（0/-1）
        """
        try:
            self.chat.append_context(message)
            self.chat.append_context(response, role='assistant')
            with open(os.path.join(current_path, self.log_file), 'a', encoding='utf-8') as f:
                f.write(
                    '--**--\n{role:s}: {content:s}\n'.format(
                        role='user_broadcast',
                        content=message
                    )
                )
                f.write(
                    '{role:s}: {content:s}\n--**--\n'.format(
                        role='broadcast_response',
                        content=response
                    )
                )
            return response
        except:
            print(f"\n广播失败{message}\n")
            return -1

    def remove_agent_context(self, beginning, ending=None):
        """
        删除上下文，并添加到日志
        :param beginning: 起
        :param ending: 止
        :return: 成功 0
        """
        removed = self.chat.remove_context(beginning, ending)
        with open(os.path.join(current_path, self.log_file), 'a', encoding='utf-8') as f:
            f.write("\n----****----\n删除上下文\n----****----\n")
            for uttr in removed:
                f.write(
                    '--**--\n{role:s}: {content:s}\n'.format(
                        role=uttr['role'],
                        content=uttr['content']
                    )
                )
            f.write("\n----****----\n删除上下文\n----****----\n")
        return 0

    def get_context(self):
        """ 返回当前对话上下文 """
        return self.chat.context
