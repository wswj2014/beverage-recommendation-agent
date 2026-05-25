import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.agent import BeverageRecommendAgent


def main():
    print("=" * 50)
    print("LUCKIN COFFEE 饮品推荐助手")
    print("输入 'clear' 清空记忆，输入 'quit' 退出")
    print("=" * 50)

    agent = BeverageRecommendAgent()

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            print("再见！")
            break
        if user_input.lower() == "clear":
            agent.clear()
            print("记忆已清空。")
            continue

        response = agent.run(user_input)
        print(f"\n助手: {response}")


if __name__ == "__main__":
    main()
