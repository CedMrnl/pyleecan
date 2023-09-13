import matplotlib.pyplot as plt
from numpy import pi, exp

from ....Classes.Arc1 import Arc1
from ....Classes.LamSlot import LamSlot
from ....Classes.Segment import Segment
from ....definitions import config_dict
from ....Functions.Plot import (
    ARROW_COLOR,
    ARROW_WIDTH,
    MAIN_LINE_COLOR,
    MAIN_LINE_STYLE,
    MAIN_LINE_WIDTH,
    P_FONT_SIZE,
    SC_FONT_SIZE,
    SC_LINE_COLOR,
    SC_LINE_STYLE,
    SC_LINE_WIDTH,
    TEXT_BOX,
    plot_quote,
)
from ....Methods import ParentMissingError

MAGNET_COLOR = config_dict["PLOT"]["COLOR_DICT"]["MAGNET_COLOR"]


def plot_schematics(
    self,
    is_default=False,
    is_add_point_label=False,
    is_add_schematics=True,
    is_add_main_line=True,
    type_add_active=1,
    save_path=None,
    is_show_fig=True,
    fig=None,
    ax=None,
):
    """Plot the schematics of the slot

    Parameters
    ----------
    self : SlotW14
        A SlotW14 object
    is_default : bool
        True: plot default schematics, else use current slot values
    is_add_point_label : bool
        True to display the name of the points (Z1, Z2....)
    is_add_schematics : bool
        True to display the schematics information (W0, H0...)
    is_add_main_line : bool
        True to display "main lines" (slot opening and 0x axis)
    type_add_active : int
        0: No active surface, 1: active surface as winding, 2: active surface as magnet, 3: active surface as winding + wedges
    save_path : str
        full path including folder, name and extension of the file to save if save_path is not None
    is_show_fig : bool
        To call show at the end of the method
    fig : Matplotlib.figure.Figure
        existing figure to use if None create a new one
    ax : Matplotlib.axes.Axes object
        Axis on which to plot the data

    Returns
    -------
    fig : Matplotlib.figure.Figure
        Figure containing the schematics
    ax : Matplotlib.axes.Axes object
        Axis containing the schematics
    """

    # Use some default parameter
    if is_default:
        slot = type(self)(Zs=12, W0=30e-3, W3=35e-3, H0=15e-3, H1=15e-3, H3=50e-3)
        lam = LamSlot(
            Rint=0.135, Rext=0.25, is_internal=False, is_stator=True, slot=slot
        )
        return slot.plot_schematics(
            is_default=False,
            is_add_point_label=is_add_point_label,
            is_add_schematics=is_add_schematics,
            is_add_main_line=is_add_main_line,
            type_add_active=type_add_active,
            save_path=save_path,
            is_show_fig=is_show_fig,
            fig=fig,
            ax=ax,
        )
    else:
        # Getting the main plot
        if self.parent is None:
            raise ParentMissingError("Error: The slot is not inside a Lamination")
        lam = self.parent
        fig, ax = lam.plot(
            alpha=pi / self.Zs, is_show_fig=False, fig=fig, ax=ax
        )  # center slot on Ox axis
        point_dict = self._comp_point_coordinate()
        if self.is_outwards():
            sign = 1
        else:
            sign = -1
        hsp = pi / self.Zs
        sp = 2 * pi / self.Zs
        Rbo = self.get_Rbo()
        # Adding point label
        if is_add_point_label:
            for name, Z in point_dict.items():
                ax.text(
                    Z.real,
                    Z.imag,
                    name,
                    fontsize=P_FONT_SIZE,
                    bbox=TEXT_BOX,
                )

        # Adding schematics
        if is_add_schematics:
            # W0
            line = Segment(point_dict["Z2"], point_dict["Z8"])
            line.plot(
                fig=fig,
                ax=ax,
                color=ARROW_COLOR,
                linewidth=ARROW_WIDTH,
                label="W0",
                offset_label=self.H0 * 0.3,
                is_arrow=True,
                fontsize=SC_FONT_SIZE,
            )
            # W3
            line = Segment(point_dict["Z4"], point_dict["Z6"] * exp(-1j * sp))
            line.plot(
                fig=fig,
                ax=ax,
                color=ARROW_COLOR,
                linewidth=ARROW_WIDTH,
                label="W3",
                offset_label=self.H0 * 0.4,
                is_arrow=True,
                fontsize=SC_FONT_SIZE,
            )
            # H0
            line = Segment(
                point_dict["Z1"] * exp(1j * sp), point_dict["Z2"] * exp(1j * sp)
            )
            line.plot(
                fig=fig,
                ax=ax,
                color=ARROW_COLOR,
                linewidth=ARROW_WIDTH,
                label="H0",
                offset_label=1j * self.W0 * 0.4,
                is_arrow=True,
                fontsize=SC_FONT_SIZE,
            )
            # H1
            Zlim1 = (
                point_dict["Z2"].real + 1j * point_dict["Z3"].imag - 1j * 0.3 * self.W3
            )
            Zlim2 = point_dict["Z3"] - 1j * 0.3 * self.W3
            plot_quote(
                point_dict["Z2"],
                Zlim1,
                Zlim2,
                point_dict["Z3"],
                offset_label=-1j * 0.5 * self.W3,
                fig=fig,
                ax=ax,
                label="H1",
            )
            # H3
            line = Segment(
                (point_dict["Z4"] * exp(1j * sp) + point_dict["Z6"]) / 2,
                (point_dict["Z3"] * exp(1j * sp) + point_dict["Z7"]) / 2,
            )
            line.plot(
                fig=fig,
                ax=ax,
                color=ARROW_COLOR,
                linewidth=ARROW_WIDTH,
                label="H3",
                offset_label=1j * self.W0 * 0.4,
                is_arrow=True,
                fontsize=SC_FONT_SIZE,
            )

        if is_add_main_line:
            # Ox axis
            line = Segment(0, lam.Rext * 1.5)
            line.plot(
                fig=fig,
                ax=ax,
                color=MAIN_LINE_COLOR,
                linestyle=MAIN_LINE_STYLE,
                linewidth=MAIN_LINE_WIDTH,
            )
            # Top arc
            line = Arc1(
                begin=Rbo * exp(-1j * pi / 2 * 0.9),
                end=Rbo * exp(1j * pi / 2 * 0.9),
                radius=Rbo,
                is_trigo_direction=True,
            )
            line.plot(
                fig=fig,
                ax=ax,
                color=MAIN_LINE_COLOR,
                linestyle=MAIN_LINE_STYLE,
                linewidth=MAIN_LINE_WIDTH,
            )
            # Tooth height
            line = Segment(point_dict["Z4"] * exp(1j * sp), point_dict["Z6"])
            line.plot(
                fig=fig,
                ax=ax,
                color=MAIN_LINE_COLOR,
                linestyle=MAIN_LINE_STYLE,
                linewidth=MAIN_LINE_WIDTH,
            )
            line = Segment(point_dict["Z3"] * exp(1j * sp), point_dict["Z7"])
            line.plot(
                fig=fig,
                ax=ax,
                color=MAIN_LINE_COLOR,
                linestyle=MAIN_LINE_STYLE,
                linewidth=MAIN_LINE_WIDTH,
            )
            # Isthmus
            line = Segment(point_dict["Z2"], point_dict["Z8"])
            line.plot(
                fig=fig,
                ax=ax,
                color=MAIN_LINE_COLOR,
                linestyle=MAIN_LINE_STYLE,
                linewidth=MAIN_LINE_WIDTH,
            )

        if type_add_active in [1, 3]:  # Wind and Wedge
            is_add_wedge = type_add_active == 3
            self.plot_active(
                fig=fig, ax=ax, is_show_fig=False, is_add_wedge=is_add_wedge
            )
        elif type_add_active == 2:  # Magnet
            self.plot_active(
                fig=fig,
                ax=ax,
                is_show_fig=False,
                enforced_default_color=MAGNET_COLOR,
            )

        elif type_add_active == 4:  # type_wedge = 1
            self.plot_active(
                fig=fig, ax=ax, is_show_fig=False, is_add_wedge=is_add_wedge
            )

        # Zooming and cleaning
        W = (point_dict["Z6"] * exp(1j * hsp)).imag
        Rint = min(point_dict["Z5"].real, point_dict["Z1"].real)
        Rext = max(point_dict["Z5"].real, point_dict["Z1"].real)

        ax.axis("equal")
        ax.set_xlim(Rint, Rext)
        ax.set_ylim(-W, W)
        manager = plt.get_current_fig_manager()
        if manager is not None:
            manager.set_window_title(type(self).__name__ + " Schematics")
        ax.set_title("")
        ax.get_legend().remove()
        ax.set_axis_off()

        # Save / Show
        if save_path is not None:
            fig.savefig(save_path)
            plt.close(fig=fig)

        if is_show_fig:
            fig.show()
        return fig, ax
