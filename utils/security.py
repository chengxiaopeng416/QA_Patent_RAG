"""
密码安全工具：使用 bcrypt 对密码进行加盐哈希与校验。

为什么用 bcrypt：
1. 自动加盐：每次哈希都会生成随机盐，相同密码产生的哈希不同，防彩虹表。
2. 自带 cost 因子：可调节计算代价，抗暴力破解。
3. 相比明文存储，数据库泄露也不会直接暴露用户密码。

注意：本项目原先是明文存储（t_user.password 曾为 String(32)）。
启用哈希后列宽须扩到 String(255) 以容纳 60 字符的 bcrypt 哈希。
"""
import bcrypt

# bcrypt 对 72 字节以上的输入会报错/截断，这里限长统一校验
BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """把明文密码加盐哈希，返回可用于存储的字符串（形如 $2b$12$...）"""
    # 转成字节，超出72字节的部分直接截断，避免 bcrypt 抛出错误
    raw = password.encode("utf-8")[:BCRYPT_MAX_BYTES]
    hashed = bcrypt.hashpw(raw, bcrypt.gensalt())
    # 返回 str（去掉 b'' 前缀）便于存入数据库
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """校验明文密码是否与已存储的 bcrypt 哈希匹配"""
    try:
        # 兼容旧数据：如果库里存的不是 bcrypt 格式（如历史明文），转成 bytes 后校验会失败
        return bcrypt.checkpw(
            password.encode("utf-8")[:BCRYPT_MAX_BYTES],
            hashed.encode("utf-8")
        )
    except (ValueError, TypeError):
        # 非法哈希（例如历史遗留的明文长度不符）统一视为校验不通过
        return False
