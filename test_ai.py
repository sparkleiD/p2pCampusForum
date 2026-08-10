# test_ai.py
"""
AI 配置测试工具

用法：
    python test_ai.py          # 测试当前配置
    python test_ai.py --debug  # 打印更详细的调试信息
"""

import os
import sys
import json

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 从 config 读取配置
try:
    from config import (
        AI_MODE,
        API_KEY, API_BASE_URL, API_MODEL_NAME,
        OLLAMA_HOST, OLLAMA_MODEL,
        AI_TIMEOUT
    )
except ImportError as e:
    print(f"❌ 无法导入 config: {e}")
    sys.exit(1)


def test_api_mode(debug=False):
    """测试 API 模式"""
    print("\n" + "=" * 60)
    print("🔍 测试 API 模式")
    print("=" * 60)

    # 1. 检查 API_KEY
    print(f"\n[1] API_KEY: {API_KEY[:10]}...{API_KEY[-4:] if len(API_KEY) > 14 else '（太短）'}")
    if not API_KEY or API_KEY == "填你的API密钥":
        print("   ❌ API_KEY 未配置")
        return False

    # 2. 检查 API_BASE_URL
    print(f"\n[2] API_BASE_URL: {API_BASE_URL}")
    if not API_BASE_URL or API_BASE_URL == "https://api.openai.com/v1":
        print("   ⚠️ 使用的是默认 OpenAI 地址，请确认是否正确")

    # 3. 检查 API_MODEL_NAME
    print(f"\n[3] API_MODEL_NAME: {API_MODEL_NAME}")
    if not API_MODEL_NAME:
        print("   ❌ API_MODEL_NAME 未配置")
        return False

    # 4. 实际调用测试
    print("\n[4] 发送测试请求...")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
            timeout=AI_TIMEOUT
        )

        response = client.chat.completions.create(
            model=API_MODEL_NAME,
            messages=[{"role": "user", "content": "请回复一个词：通过"}],
            max_tokens=50,
            temperature=0.1
        )

        raw = response.choices[0].message.content
        print(f"   ✅ API 调用成功")
        print(f"   📝 返回内容: {raw}")

        if debug:
            print(f"\n📦 完整响应:")
            print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))

        return True

    except Exception as e:
        print(f"   ❌ API 调用失败: {type(e).__name__}: {e}")

        # 给出更具体的建议
        error_msg = str(e).lower()
        if "authentication" in error_msg:
            print("   💡 建议: 检查 API_KEY 是否正确")
        elif "connection" in error_msg or "connect" in error_msg:
            print(f"   💡 建议: 检查网络连接，确认 API_BASE_URL 是否可访问")
        elif "timeout" in error_msg:
            print(f"   💡 建议: 网络较慢，尝试增加 AI_TIMEOUT")
        elif "model" in error_msg:
            print(f"   💡 建议: 检查 API_MODEL_NAME 是否正确")
        elif "rate" in error_msg or "limit" in error_msg:
            print(f"   💡 建议: 请求太频繁，稍后重试")
        elif "balance" in error_msg or "quota" in error_msg:
            print(f"   💡 建议: 账户余额不足，请充值")

        return False


def test_local_mode(debug=False):
    """测试本地 Ollama 模式"""
    print("\n" + "=" * 60)
    print("🔍 测试本地 Ollama 模式")
    print("=" * 60)

    # 1. 检查 Ollama 主机
    print(f"\n[1] OLLAMA_HOST: {OLLAMA_HOST}")
    print(f"[2] OLLAMA_MODEL: {OLLAMA_MODEL}")

    # 2. 检查连接
    print("\n[3] 检查 Ollama 服务是否运行...")
    try:
        import requests
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            print(f"   ✅ Ollama 服务运行中")
            print(f"   📦 已安装模型: {model_names}")

            if OLLAMA_MODEL not in model_names:
                print(f"   ⚠️ 模型 {OLLAMA_MODEL} 未安装")
                print(f"   💡 运行: ollama pull {OLLAMA_MODEL}")
                return False
        else:
            print(f"   ❌ Ollama 服务异常: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ 无法连接到 Ollama")
        print(f"   💡 请确保 Ollama 已启动: ollama serve")
        return False
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        return False

    # 3. 测试推理
    print("\n[4] 发送测试请求...")
    try:
        import requests
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": "请回复一个词：通过",
                "stream": False
            },
            timeout=AI_TIMEOUT
        )
        raw = response.json().get("response", "")
        print(f"   ✅ 推理成功")
        print(f"   📝 返回内容: {raw}")
        return True

    except Exception as e:
        print(f"   ❌ 推理失败: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI 配置测试工具")
    parser.add_argument("--debug", action="store_true", help="打印详细调试信息")
    args = parser.parse_args()

    print("=" * 60)
    print("🧪 AI 配置测试工具")
    print("=" * 60)
    print(f"当前 AI 模式: {AI_MODE}")
    print(f"超时时间: {AI_TIMEOUT} 秒")

    if AI_MODE == "api":
        success = test_api_mode(debug=args.debug)
    elif AI_MODE == "local":
        success = test_local_mode(debug=args.debug)
    else:
        print(f"❌ 未知的 AI_MODE: {AI_MODE}")
        success = False

    print("\n" + "=" * 60)
    if success:
        print("✅ 所有测试通过，AI 配置正常")
    else:
        print("❌ 测试失败，请根据上面的提示检查配置")
    print("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()