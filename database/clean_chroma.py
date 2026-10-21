# -*- coding: utf-8 -*-
"""
Chroma 向量数据库清理工具（独立脚本，不依赖项目其他模块）

【PyCharm 一键运行】
  直接在 PyCharm 里右键 Run / 点绿色运行按钮即可。
  默认动作：清空项目集合 'PatentRAG_default' 内的所有向量（保留空集合），
  仅操作这一个集合，绝不触碰其他集合、文件或软件。

【可选命令行参数】（PyCharm 里 Run 时无需传参，直接用默认即可）
  python clean_chroma.py                      # 默认：清空 PatentRAG_default 内所有向量
  python clean_chroma.py --list               # 只列出所有集合，不修改
  python clean_chroma.py --delete             # 删除整个目标集合（集合移除）
  python clean_chroma.py --collection X       # 指定其它目标集合名，默认 PatentRAG_default
  python clean_chroma.py --host H --port P    # 指定 Chroma 服务器地址/端口

提示：
  请用与本项目相同的 python 环境（已安装 chromadb）运行，例如 agent_env。
"""

import argparse
import sys

# 让 Windows 控制台正常显示中文（忽略 GBK 下部分字符无法打印的报错）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8081
# 默认只操作的项目集合名；可用 --collection 覆盖
DEFAULT_COLLECTION = "PatentRAG_default"

CHROMA_PYHON_HINT = (
    "\n" "=" * 60 + "\n"
    "  请在 PyCharm 中把解释器切换为：\n"
    "  D:\\Programdata\\anaconda3\\envs\\agent_env\\python.exe\n"
    "  或使用已安装 chromadb 的环境。\n"
    "  否则本脚本无法连接 Chroma。\n"
    "=" * 60 + "\n"
)


def get_client(host, port):
    import chromadb

    return chromadb.HttpClient(host=host, port=port)


def list_collections(client):
    """返回 [(集合名, 向量数), ...]"""
    collections = client.list_collections()
    result = []
    for col in collections:
        try:
            result.append((col.name, col.count()))
        except Exception as e:  # 某些集合可能读取失败，单独记录
            result.append((col.name, f"<读取失败: {e}>"))
    return result


def print_collections(collections):
    if not collections:
        print("（服务器上没有集合）")
        return
    print(f"{'集合名称':<40}{'向量数量':>12}")
    print("-" * 54)
    for name, count in collections:
        print(f"{name:<40}{str(count):>12}")
    print("-" * 54)


def find_collection(client, name):
    """安全获取指定集合，不存在则返回 None"""
    try:
        col = client.get_collection(name)
        return col
    except Exception:
        return None


def confirm(prompt: str) -> bool:
    """交互二次确认"""
    while True:
        ans = input(f"{prompt} [y/N]: ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no", ""):
            return False
        print("请输入 y 或 n")


def clear_collection_vectors(col, collection_name):
    """清空指定集合内所有向量（保留集合本身），返回清空的向量条数"""
    count = col.count()
    if count > 0:
        ids = col.get(include=[])["ids"]
        batch = 200
        for i in range(0, len(ids), batch):
            col.delete(ids=ids[i:i + batch])
    print(f"[+] 已清空集合 '{collection_name}' 内的 {count} 条向量。")
    return count


def main():
    parser = argparse.ArgumentParser(
        description="清理 Chroma 向量数据库中的集合或向量（精确、安全）"
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Chroma 服务器地址（默认 {DEFAULT_HOST}）")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Chroma 服务器端口（默认 {DEFAULT_PORT}）")
    parser.add_argument("--collection", default=DEFAULT_COLLECTION,
                        help=f"目标集合名（默认 {DEFAULT_COLLECTION}）")
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument("--delete", action="store_true",
                      help="删除整个指定集合（集合被移除）")
    dest.add_argument("--list", action="store_true",
                      help="只列出所有集合，不修改")
    args = parser.parse_args()

    print(f"正在连接 Chroma 服务器 {args.host}:{args.port} ...")
    try:
        client = get_client(args.host, args.port)
    except Exception as e:
        print(f"[-] 连接失败：{e}")
        print("    请确认 Chroma 服务已启动，或使用 --host / --port 指定正确地址。")
        print(CHROMA_PYHON_HINT)
        input("按回车键退出...")
        return

    # 只读列出所有集合
    print("\n===== Chroma 现有集合及向量数 =====")
    print_collections(list_collections(client))

    if args.list:
        print("\n[只读] 已列出，未做任何修改。")
        input("按回车键退出...")
        return

    if args.delete:
        # 精确校验目标集合是否存在
        col = find_collection(client, args.collection)
        if col is None:
            print(f"\n[-] 目标集合 '{args.collection}' 不存在，操作取消（未做任何修改）。")
            input("按回车键退出...")
            return
        target_count = col.count()
        prompt = (f"\n即将【永久删除】整个集合 '{args.collection}'"
                  f"（当前含 {target_count} 条向量），此操作不可恢复，确认继续？")
        if not confirm(prompt):
            print("已取消，未做任何修改。")
        else:
            client.delete_collection(args.collection)
            print(f"[+] 已删除集合 '{args.collection}'。")
    else:
        # 默认动作（PyCharm 直接 Run）：清空目标集合内所有向量
        col = find_collection(client, args.collection)
        if col is None:
            print(f"\n[-] 目标集合 '{args.collection}' 不存在，操作取消（未做任何修改）。")
            input("按回车键退出...")
            return
        target_count = col.count()
        prompt = (f"\n即将【清空】集合 '{args.collection}' 内的全部 {target_count} 条向量"
                  f"（集合本身保留），此操作不可恢复，确认继续？")
        if not confirm(prompt):
            print("已取消，未做任何修改。")
        else:
            clear_collection_vectors(col, args.collection)

    print("\n===== 清理后状态 =====")
    print_collections(list_collections(client))
    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
