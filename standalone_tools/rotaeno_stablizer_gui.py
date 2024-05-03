from ttkbootstrap import Window
from rotaeno_stablizer.gui import Gui

if __name__ == "__main__":
    app = Window("Rotaeno Stablizer", "darkly")
    Gui(app)
    app.mainloop()