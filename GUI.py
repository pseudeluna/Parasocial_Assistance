import os
import sys
import threading
import tkinter as tk
import tkinter.filedialog as tkFileDialog
import winsound
from typing import Optional

from main import (
    CHECK_INTERVAL_SECONDS,
    download_video,
    find_new_video_ids,
    get_channel_video_ids,
    is_valid_channel_url,
)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(
            os.path.abspath(__file__)
        )

    return os.path.join(base_path, relative_path)
ICON_PATH = resource_path("PA.ico")

def play_download_notification():
    try:
        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
    except RuntimeError:
        winsound.MessageBeep(winsound.MB_ICONASTERISK)


def run_app():
    monitoring = False
    known_video_ids: set[str] = set()
    check_job = None

    root = tk.Tk()
    root.title("Parasocial Assist")
    if os.path.isfile(ICON_PATH):
        root.iconbitmap(ICON_PATH)
        
    tk.Label(
        root, text="Automate downloading every newest video from your fav channel"
    ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))

    tk.Label(root, text="Channel: ").grid(row=1, sticky=tk.W)
    txt_Channel = tk.Entry(root, width=50)
    txt_Channel.grid(row=1, column=1, columnspan=2, sticky=tk.W)

    tk.Label(root, text="Settings").grid(row=2, sticky=tk.W, pady=(8, 0))

    check_Quality = tk.IntVar(value=2)
    tk.Radiobutton(
        root,
        text="Download with Lowest Resolution",
        variable=check_Quality,
        value=1,
    ).grid(row=3, sticky=tk.W)
    tk.Radiobutton(
        root,
        text="Download with Highest Resolution",
        variable=check_Quality,
        value=2,
    ).grid(row=4, sticky=tk.W)

    path_var = tk.StringVar()

    def pathfilled():
        dirname = tkFileDialog.askdirectory(
            parent=root, initialdir="/", title="Select Path to Save to:"
        )
        if dirname:
            path_var.set(dirname)

    tk.Label(root, text="Select Path to Save to: ").grid(row=5, sticky=tk.W)
    tk.Entry(root, width=30, textvariable=path_var).grid(row=5, column=1, sticky=tk.W)
    tk.Button(root, text="Browse", command=pathfilled).grid(row=5, column=2)

    status_var = tk.StringVar(value="")
    status_frame = tk.Frame(root, relief=tk.GROOVE, borderwidth=1, padx=8, pady=8)
    tk.Label(status_frame, textvariable=status_var, fg="blue", wraplength=420, justify=tk.LEFT).pack(
        anchor=tk.W
    )

    def show_status(message: str):
        status_var.set(message)
        status_frame.grid(row=7, column=0, columnspan=3, sticky=tk.W, pady=(8, 8))

    def get_settings():
        return {
            "channel_url": txt_Channel.get().strip(),
            "save_path": path_var.get().strip(),
            "quality": check_Quality.get(),
        }

    def validate_settings(settings: dict) -> Optional[str]:
        if not settings["channel_url"]:
            return "Enter a channel URL."
        if not is_valid_channel_url(settings["channel_url"]):
            return "Enter a valid YouTube channel URL."
        if not settings["save_path"]:
            return "Select a folder to save videos."
        if settings["quality"] not in (1, 2):
            return "Choose a download quality."
        if not os.path.isdir(settings["save_path"]):
            return "Save folder does not exist."
        return None

    def schedule_next_check():
        nonlocal check_job
        if not monitoring:
            return
        check_job = root.after(CHECK_INTERVAL_SECONDS * 1000, run_check)

    def run_check():
        settings = get_settings()
        error = validate_settings(settings)
        if error:
            show_status(error)
            schedule_next_check()
            return

        def work():
            try:
                new_ids = find_new_video_ids(settings["channel_url"], known_video_ids)
                if not new_ids:
                    root.after(
                        0,
                        lambda: show_status(
                            f"No new videos. Checking again in {CHECK_INTERVAL_SECONDS}s..."
                        ),
                    )
                    root.after(0, schedule_next_check)
                    return

                downloaded_titles = []
                for video_id in new_ids:
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    title = download_video(
                        video_url,
                        settings["quality"],
                        settings["save_path"],
                    )
                    known_video_ids.add(video_id)
                    downloaded_titles.append(title)

                summary = ", ".join(downloaded_titles)

                def on_download_complete():
                    show_status(
                        f"Downloaded: {summary}\nChecking again in {CHECK_INTERVAL_SECONDS}s..."
                    )
                    play_download_notification()

                root.after(0, on_download_complete)
            except Exception as exc:
                root.after(0, lambda: show_status(f"Error: {exc}"))
            finally:
                root.after(0, schedule_next_check)

        threading.Thread(target=work, daemon=True).start()

    def on_save():
        nonlocal monitoring, known_video_ids, check_job

        settings = get_settings()
        error = validate_settings(settings)
        if error:
            show_status(error)
            return

        if check_job is not None:
            root.after_cancel(check_job)
            check_job = None

        monitoring = False
        known_video_ids = set()
        show_status("Checking channel...")

        def work():
            nonlocal monitoring, known_video_ids
            try:
                known_video_ids = get_channel_video_ids(settings["channel_url"])
                monitoring = True
                root.after(
                    0,
                    lambda: show_status(
                        f"Monitoring {len(known_video_ids)} existing video(s). "
                        f"New uploads will download automatically every "
                        f"{CHECK_INTERVAL_SECONDS}s."
                    ),
                )
                root.after(0, schedule_next_check)
            except Exception as exc:
                monitoring = False
                root.after(0, lambda: show_status(f"Error: {exc}"))

        threading.Thread(target=work, daemon=True).start()

    tk.Button(root, text="Save", width=15, command=on_save).grid(row=6, sticky=tk.W, pady=(8, 0))

    root.mainloop()


if __name__ == "__main__":
    run_app()
