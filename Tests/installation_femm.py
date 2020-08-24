from pywinauto.application import Application
import pywinauto
import time

import urllib.request

print("Downloading FEMM installer")
url = "http://www.femm.info/wiki/Files/files.xml?action=download&file=femm42bin_x64_21Apr2019.exe"
urllib.request.urlretrieve(url, "femm42bin_x64_21Apr2019.exe")
print("Done")

print("Installing FEMM...")

# app = Application(backend="uia").start("femm42bin_x64_21Apr2019.exe")
app = Application().start("femm42bin_x64_21Apr2019.exe")
time.sleep(5)

# Connect to FEMM Setup
app.connect(best_match="Setup")
window = app.top_window()

# First page: License Agreement
window.RadioButton0.click()  # I accept the agreements
window.Button.click()  # Next

# Second page: Select Destination Location
window.Button3.click()

# Third page: Select Start Menu Folder
window.Button3.click()

# Fourth page: Ready to Install
window.Button2.click()

# Close the Setup programm
window.Button0.click()

