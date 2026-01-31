"""CFGPT 类，用于智能体调用金融知识模型"""
import torch
import os
import gc
from transformers import AutoTokenizer, AutoModelForCausalLM
# 获取当前程序的路径
current_path = os.path.dirname(os.path.abspath(__file__))

# 从 CFGPT_path.txt 中读取路径
with open(os.path.join(current_path, 'CFGPT_path.txt'), 'r', encoding='utf-8') as f:
    CFGPT_path = f.read().strip()
tokenizer = AutoTokenizer.from_pretrained(CFGPT_path, trust_remote_code=True)
# Set `torch_dtype=torch.float16` to load model in float16, otherwise it will be loaded as float32 and cause OOM Error.
model = AutoModelForCausalLM.from_pretrained(CFGPT_path, torch_dtype=torch.float16, trust_remote_code=True, device_map="auto")
model = model.eval()

class CFGPT:
    """CFGPT 类，仅支持单轮对话"""
    def __init__(self):
        """
        初始化时清空历史
        """
        self.history = []

    def clear_history(self):
        """
        清空历史，开启新的对话
        :return: 0
        """
        self.history.clear()
        return 0

    def chat_with_history(self, prompt):
        """
        保存历史的对话
        :param prompt: 提示词
        :return: 响应，仅文本
        """
        response, self.history = model.chat(tokenizer, prompt, history=self.history, temperature=0.5, top_p=0.5)
        return response

    def news_analysis(self, news: str):
        """
        新闻分析，使用提示词模板 expert_news_analysis_0.txt
        暂定单论对话
        :param news: 新闻内同
        :return: 分析结果 - str
        """
        turns = 1
        with open(os.path.join(current_path, "templates/expert/expert_news_analysis_0.txt"), 'r', encoding='utf-8') as f:
            prompts = f.read().split('-----*****-----\n')

        # 清除历史，开始对话
        self.clear_history()
        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    news=news
                )
                return self.chat_with_history(prompt)

    def advise_to_agent(self, identity: str,  strategy: str):
        """
        使专家评估智能体的期货下单策略，以提高行为专业性
        :param strategy: 智能体在本轮次出价的策略
        :return: 专家建议 - str
        """
        turns = 1
        with open(os.path.join(current_path, "templates/expert/expert_advise_0.txt"), 'r', encoding='utf-8') as f:
            prompts = f.read().split('-----*****-----\n')

        # 清除历史，开始对话
        self.clear_history()
        for i in range(turns):
            if i == 0:
                prompt = prompts[i].format(
                    identity=identity,
                    strategy=strategy
                )
                return self.chat_with_history(prompt)

    def without_expert(self):
        '''
        消融实验
        :return: 固定回复，专家没有给出意见
        '''
        return "专家没有给出任何意见，请保持你原本的判断"
