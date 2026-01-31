import numpy as np
import faiss
import torch
import json
import argparse
from modelscope import AutoModel, AutoConfig, AutoTokenizer, snapshot_download

device = 'cuda:1'
model_dir = snapshot_download('AI-ModelScope/roberta-large', revision='master')
tokenizer = AutoTokenizer.from_pretrained(model_dir, device_map=device)
model = AutoModel.from_pretrained(model_dir, device_map=device)
model.eval()


def normalize_vector(vec):
    """归一化向量，用于余弦相似度计算"""
    norm = np.linalg.norm(vec)
    if norm > 0:
        return vec / norm
    return vec


def retrieve_query(query):
    index_path = 'vectors_index_faiss_test_1.index' # 数据路径
    k = 2    # 返回结果数量

    # 加载FAISS索引
    # print(f"正在加载索引: {index_path}")
    index = faiss.read_index(index_path)

    # 获取向量维度
    # dimension = index.d
    # print(f"索引向量维度: {dimension}")
    # print(f"索引中向量总数: {index.ntotal}")

    try:
        with torch.no_grad():
            encoded_input = tokenizer(query, return_tensors='pt').to(device)
            output = model(**encoded_input).pooler_output.to('cpu').numpy()[0]

        # 解析用户输入的向量
        try:
            query_vector = np.array([output], dtype=np.float32)

            # 如果是余弦相似度索引，需要归一化查询向量
            # 如果不确定索引类型，可以尝试检测或总是归一化向量
            query_vector = normalize_vector(query_vector)

            # 执行查询
            # print("执行查询...")
            distances, indices = index.search(query_vector, k)

            del encoded_input, output

            # 显示结果
            # print(f"\n找到最接近的 {k} 个结果:")
            with open('documents.json', 'r') as doc_file:
                docs = json.load(doc_file)
                returnList = []
                for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
                    # 对于内积/余弦相似度，值越大越相似
                    # 对于L2距离，值越小越相似
                    similarity = dist  # 如果是内积/余弦相似度
                    # similarity = 1 / (1 + dist)  # 如果是L2距离，转换为相似度

                    # print(f"#{i+1}: 索引 ID = {idx}, 相似度 = {similarity:.6f}")
                    # print('document:', docs[str(idx)])
                    returnList.append(docs[str(idx)])
                return returnList

        except ValueError as e:
            print(f"错误: 无法解析输入向量: {e}")
            return None

    except KeyboardInterrupt:
        print("\n程序被用户中断")
        return None


if __name__ == '__main__':
    test_query = '芝加哥期货交易所大豆商品SF2503期货价格总体保持稳定，在小范围内保持震荡，没有异动。'
    print(retrieve_query(test_query))

