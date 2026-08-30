def run(params):
    """
    参数:
      params: dict, 包含 "celsius" 或 "fahrenheit"
    返回:
      dict, 转换结果
    """
    if "celsius" in params:
        c = float(params["celsius"])
        f = c * 9 / 5 + 32
        return {"fahrenheit": f}
    elif "fahrenheit" in params:
        f = float(params["fahrenheit"])
        c = (f - 32) * 5 / 9
        return {"celsius": c}
    else:
        raise ValueError("params must contain 'celsius' or 'fahrenheit'")
