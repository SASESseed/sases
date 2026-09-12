# Auto-generated Harness module from work log #22
def run(params=None):
    """返回原始命令输出，供后续参考"""
    command = "dir && echo hacked"
    output = "参数包含危险字符: &&"
    status = "blocked"
    return {
        "command": command,
        "status": status,
        "output": output
    }
