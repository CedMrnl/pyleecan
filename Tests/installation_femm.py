from pywinauto.application import Application
import pywinauto
import time

import urllib.request
import os
import subprocess
from shutil import copyfile

# print("Downloading FEMM installer")
# url = "http://www.femm.info/wiki/Files/files.xml?action=download&file=femm42bin_x64_21Apr2019.exe"
# urllib.request.urlretrieve(url, "femm42bin_x64_21Apr2019.exe")
# print("Done")

# print("Installing FEMM...")
os.system("choco new femm")

copyfile("Tests/femm.nuspec", "Tests/femm/femm.nuspec")
copyfile("chocolateyinstall.ps1", "Tests/femm/tools/chocolateyinstall.ps1")
os.system("choco pack Tests/femm/femm.nuspec")
process = subprocess.Popen(["choco", "install", "Tests/femm.1.0.0.nupkg", "-y"])
# app = Application(backend="uia").start("femm42bin_x64_21Apr2019.exe")
# app = Application().start("femm42bin_x64_21Apr2019.exe")
time.sleep(25)
try:
    # Connect to FEMM Setup
    app = Application()
    app.connect(best_match="Setup")
    window = app.top_window()

    print(window)
    # First page: License Agreement
    window.RadioButton0.click()  # I accept the agreements
    window.Button.click()  # Next

    # Second page: Select Destination Location
    window.Button3.click()

    # Third page: Select Start Menu Folder
    window.Button3.click()

    # Fourth page: Ready to Install
    window.Button2.click()
    time.sleep(30)

    # Close the Setup programm
    window.Button0.click()

finally:
    process.kill()
