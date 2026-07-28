"""
贪吃蛇小游戏 - 终端版
使用方向键控制蛇的移动，吃到食物得分，撞墙或撞到自己游戏结束。
"""

import curses
import random
import time


def main(stdscr):
    # 初始化设置
    curses.curs_set(0)  # 隐藏光标
    stdscr.nodelay(1)   # 非阻塞输入
    stdscr.timeout(100) # 刷新间隔(毫秒)，控制游戏速度

    # 获取终端尺寸
    sh, sw = stdscr.getmaxyx()
    # 游戏区域
    box_h = sh - 2
    box_w = sw - 2

    # 初始蛇：长度3，水平居中偏左
    snake = [
        [box_h // 2, box_w // 2],
        [box_h // 2, box_w // 2 - 1],
        [box_h // 2, box_w // 2 - 2],
    ]
    direction = curses.KEY_RIGHT  # 初始方向向右

    # 随机生成食物
    food = [random.randint(1, box_h - 2), random.randint(1, box_w - 2)]
    # 确保食物不在蛇身上
    while food in snake:
        food = [random.randint(1, box_h - 2), random.randint(1, box_w - 2)]

    score = 0

    # 绘制边框
    stdscr.clear()
    for y in range(box_h):
        stdscr.addch(y, 0, '│')
        stdscr.addch(y, box_w - 1, '│')
    for x in range(box_w):
        stdscr.addch(0, x, '─')
        stdscr.addch(box_h - 1, x, '─')
    stdscr.addch(0, 0, '┌')
    stdscr.addch(0, box_w - 1, '┐')
    stdscr.addch(box_h - 1, 0, '└')
    stdscr.addch(box_h - 1, box_w - 1, '┘')

    while True:
        # 获取键盘输入
        key = stdscr.getch()

        # 方向控制（不能反向）
        if key == curses.KEY_UP and direction != curses.KEY_DOWN:
            direction = curses.KEY_UP
        elif key == curses.KEY_DOWN and direction != curses.KEY_UP:
            direction = curses.KEY_DOWN
        elif key == curses.KEY_LEFT and direction != curses.KEY_RIGHT:
            direction = curses.KEY_LEFT
        elif key == curses.KEY_RIGHT and direction != curses.KEY_LEFT:
            direction = curses.KEY_RIGHT
        elif key == ord('q'):
            break  # 按 q 退出

        # 计算新蛇头位置
        head = snake[0].copy()
        if direction == curses.KEY_UP:
            head[0] -= 1
        elif direction == curses.KEY_DOWN:
            head[0] += 1
        elif direction == curses.KEY_LEFT:
            head[1] -= 1
        elif direction == curses.KEY_RIGHT:
            head[1] += 1

        # 在头部插入新位置
        snake.insert(0, head)

        # 判断是否吃到食物
        if head == food:
            score += 10
            # 生成新食物
            food = [random.randint(1, box_h - 2), random.randint(1, box_w - 2)]
            while food in snake:
                food = [random.randint(1, box_h - 2), random.randint(1, box_w - 2)]
        else:
            # 移除尾部
            snake.pop()

        # 绘制游戏画面
        stdscr.clear()

        # 绘制边框
        for y in range(box_h):
            stdscr.addch(y, 0, '│')
            stdscr.addch(y, box_w - 1, '│')
        for x in range(box_w):
            stdscr.addch(0, x, '─')
            stdscr.addch(box_h - 1, x, '─')
        stdscr.addch(0, 0, '┌')
        stdscr.addch(0, box_w - 1, '┐')
        stdscr.addch(box_h - 1, 0, '└')
        stdscr.addch(box_h - 1, box_w - 1, '┘')

        # 绘制蛇身
        for i, seg in enumerate(snake):
            y, x = seg
            if 0 < y < box_h - 1 and 0 < x < box_w - 1:
                if i == 0:
                    stdscr.addch(y, x, '●')  # 蛇头
                else:
                    stdscr.addch(y, x, '○')  # 蛇身

        # 绘制食物
        if 0 < food[0] < box_h - 1 and 0 < food[1] < box_w - 1:
            stdscr.addch(food[0], food[1], '★')

        # 判断碰撞：撞墙
        if (
            head[0] <= 0
            or head[0] >= box_h - 1
            or head[1] <= 0
            or head[1] >= box_w - 1
        ):
            break

        # 判断碰撞：撞到自己
        if head in snake[1:]:
            break

        # 显示分数
        score_text = f"  Score: {score}  "
        stdscr.addstr(sh - 1, (sw - len(score_text)) // 2, score_text)

        stdscr.refresh()

    # 游戏结束画面
    stdscr.clear()
    game_over = "=== GAME OVER ==="
    final_score = f"Final Score: {score}"
    restart_text = "Press any key to exit..."

    stdscr.addstr(sh // 2 - 1, (sw - len(game_over)) // 2, game_over)
    stdscr.addstr(sh // 2, (sw - len(final_score)) // 2, final_score)
    stdscr.addstr(sh // 2 + 1, (sw - len(restart_text)) // 2, restart_text)
    stdscr.refresh()

    stdscr.nodelay(0)
    stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main)
