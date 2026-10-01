"""Stalzone Main — генератор app.ico для .exe."""
from icons import create_window_icon

if __name__ == "__main__":
    img = create_window_icon(256)
    img.save(
        "app.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
               (64, 64), (128, 128), (256, 256)],
    )
    print("app.ico создан")