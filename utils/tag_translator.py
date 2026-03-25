from typing import List
import os
import openai

class TagTranslator:
    def __init__(self, model, api_address, api_key):
        self.model = model
        self.api_address = api_address
        self.api_key = api_key
        self.sys_prompt ='''
            你是一个tag翻译器，负责将用户输入的danbooru tag翻译成中文。请根据以下要求进行翻译：
            1. 只翻译tag，不要添加任何解释或额外信息。
            2. 保持tag的原有格式，翻译时只替换其中的英文部分。
            3. 如果tag中包含下划线，翻译时将下划线替换为空格。
            4. 如果tag中包含括号，翻译时将括号转义，已转义的括号不需要再次转义。
            5. 请查找tag的准确翻译，避免使用不相关或错误的词汇。
            6. 人名翻译参照萌娘百科，如果tag中包含人名，请使用萌娘百科上的翻译。
        '''
        self.openai = openai.OpenAI(api_key=self.api_key, base_url=self.api_address)


    def batch(self, file: str)->List[List[str]]:
        pass

    
    def translate(self, tags: List[str])->List[str]:
        pass

    