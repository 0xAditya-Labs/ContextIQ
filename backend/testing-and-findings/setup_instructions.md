# Resolving "Cannot find module langchain_google_genai" in VS Code

Even if your terminal has activated the virtual environment (`venv`), VS Code's editor engine (Pylance) might still be looking at your global Python installation, showing red squiggly lines on imports.

Follow these quick steps to fix it:

## Step 1: Open the Select Interpreter Menu
1. Press the keys **`Ctrl` + `Shift` + `P`** (Windows) or **`Cmd` + `Shift` + `P`** (Mac) at the same time to open the VS Code Command Palette.
2. In the search box that pops up at the top, type:
   ```text
   Python: Select Interpreter
   ```
3. Click on the option **`Python: Select Interpreter`**.

---

## Step 2: Choose your Virtual Environment
* You should see a list of Python installations on your computer.
* Look for the option that points to the environment we created:
  ```text
  Python 3.x.x ('venv': venv) - .\venv\Scripts\python.exe
  ```
* **Click on it** to select it.

---

## Step 3: (Optional) If it is not listed
If your `venv` doesn't show up in the list:
1. Choose **`Enter interpreter path...`** at the top of the list.
2. Click **`Find...`** (or browse).
3. Navigate to your project folder: `backend/venv/Scripts/` and select **`python.exe`**.

---

Once selected, VS Code will use the packages installed inside your virtual environment, and the error/warning will go away!
