#!/usr/bin/env python3
"""
TOTP功能测试脚本
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pyotp

from app.core.security import (
    generate_totp_qr_code_url,
    generate_totp_secret,
    verify_totp_code,
)


def test_totp_basic_functionality():
    """测试TOTP基本功能"""
    print("🧪 测试TOTP基本功能...")

    # 1. 生成TOTP密钥
    secret = generate_totp_secret()
    print(f"✓ 生成TOTP密钥: {secret}")

    # 2. 生成TOTP代码（模拟用户的验证器应用）
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    print(f"✓ 当前TOTP代码: {current_code}")

    # 3. 验证TOTP代码
    is_valid = verify_totp_code(secret, current_code)
    print(f"✓ TOTP代码验证: {'通过' if is_valid else '失败'}")

    # 4. 测试错误代码
    invalid_code = "123456"
    is_invalid = verify_totp_code(secret, invalid_code)
    print(f"✓ 错误代码验证: {'失败' if not is_invalid else '意外通过'}")

    # 5. 生成二维码URL
    qr_url = generate_totp_qr_code_url(secret, "test_user", "MaterialBin")
    print(
        f"✓ 二维码生成: {'成功' if qr_url.startswith('data:image/png;base64,') else '失败'}"
    )

    return is_valid and not is_invalid and qr_url.startswith("data:image/png;base64,")


def test_totp_time_window():
    """测试TOTP时间窗口"""
    print("\n🕒 测试TOTP时间窗口...")

    secret = generate_totp_secret()
    totp = pyotp.TOTP(secret)

    # 当前时间的代码
    current_code = totp.now()
    print(
        f"✓ 当前代码验证: {'通过' if verify_totp_code(secret, current_code) else '失败'}"
    )

    # 模拟30秒前的代码（TOTP通常有30秒的容错）
    import time

    previous_time = int(time.time()) - 30
    previous_code = totp.at(previous_time)
    print(
        f"✓ 前一时段代码验证: {'通过' if verify_totp_code(secret, previous_code) else '失败'}"
    )

    return True


def main():
    """主测试函数"""
    print("🚀 开始TOTP功能测试")
    print("=" * 50)

    try:
        # 基本功能测试
        basic_test_passed = test_totp_basic_functionality()

        # 时间窗口测试
        time_test_passed = test_totp_time_window()

        print("\n" + "=" * 50)
        print("📊 测试结果:")
        print(f"   基本功能: {'✓ 通过' if basic_test_passed else '✗ 失败'}")
        print(f"   时间窗口: {'✓ 通过' if time_test_passed else '✗ 失败'}")

        if basic_test_passed and time_test_passed:
            print("\n🎉 所有TOTP测试通过！")
            return True
        else:
            print("\n❌ 部分测试失败")
            return False

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
