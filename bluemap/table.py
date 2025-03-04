from typing import Literal

import PIL
from PIL import ImageDraw
from PIL.ImageFont import ImageFont, FreeTypeFont

Color = tuple[int, int, int] | tuple[int, int, int, int]


class Cell:
    def __init__(
            self,
            text: str,
            color: Color,
            bg_color: Color = (0, 0, 0, 0),
            font: ImageFont | FreeTypeFont | None = None,
            anchor: Literal["ls", "lt", "lm", "ms", "mt", "mm", "rs", "rt", "rm"] = "ls",
    ):
        self.text = text
        self.color = color
        self.bg_color = bg_color
        self.font = font
        self._dimensions: tuple[int, int] | None = None
        self.anchor = anchor


class Row:
    def __init__(self, cells):
        self.cells: list[Cell] = cells

class Table:
    def __init__(
            self,
            table_color: Color,
            cell_padding: tuple[int, int, int, int] = (2, 3, 2, 3),
            fixed_col_widths: list[float] | None = None,
    ):
        """
        Create a new table
        :param table_color: the color for the table lines
        :param cell_padding: padding for each cell (left, top, right, bottom)
        """
        self.rows: list[Row] = []
        self.h_lines: list[int] = []
        self.table_color = table_color
        self.cell_padding = cell_padding
        self.font = PIL.ImageFont.load_default()
        self.fixed_col_widths = fixed_col_widths

    def _get_num_cols(self):
        return max(len(row.cells) for row in self.rows)

    def add_row(
            self,
            text: list[str],
            color: list[Color],
            *,
            anchors: list[Literal["ls", "lt", "lm", "ms", "mt", "mm", "rs", "rt", "rm"]] | None = None,
            bg_color: Color | None = None,
    ):
        cells = [Cell(
            text[i] if text[i] else "",
            color[i],
            anchor=anchors[i] if anchors and i < len(anchors) else "ls",
            bg_color=bg_color,
        ) for i in range(len(text))]
        self.rows.append(Row(cells))

    def add_h_line(self):
        self.h_lines.append(len(self.rows))

    def render(
            self,
            draw: ImageDraw.ImageDraw,
            xy: tuple[int, int],
    ):
        col_widths: list[float] = [10.0] * self._get_num_cols()
        row_heights: list[float] = [10.0] * len(self.rows)
        def_font = self.font

        # Calculate dimensions
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row.cells):
                font = cell.font or def_font
                bbox = draw.textbbox((50, 50), cell.text, font=font)
                height = font.getmetrics()[0]
                width = bbox[2] - bbox[0]
                width += self.cell_padding[0] + self.cell_padding[2]
                height += self.cell_padding[1] + self.cell_padding[3]
                col_widths[c] = max(col_widths[c], width)
                row_heights[r] = max(row_heights[r], height)
        if self.fixed_col_widths:
            col_widths = self.fixed_col_widths
        xy = (xy[0], xy[1])
        col_starts = [0.0]
        for i in range(1, len(col_widths)):
            col_starts.append(col_starts[i-1] + col_widths[i-1])

        row_start = row_heights[0] / 2
        # Draw cells
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row.cells):
                if cell.anchor[0] == "l":
                    x = xy[0] + col_starts[c]
                    x += self.cell_padding[0]
                elif cell.anchor[0] == "m":
                    x = xy[0] + col_starts[c] + col_widths[c] / 2
                elif cell.anchor[0] == "r":
                    x = xy[0] + col_starts[c] + col_widths[c]
                    x -= self.cell_padding[2]
                else:
                    raise ValueError(f"Invalid anchor: {cell.anchor}")
                if cell.anchor[1] == "s":
                    y = xy[1] + sum(row_heights[:r]) + row_start
                    y += self.cell_padding[1]
                elif cell.anchor[1] == "m":
                    y = xy[1] + sum(row_heights[:r]) + row_heights[r] / 2 +  + row_start
                elif cell.anchor[1] == "t":
                    y = xy[1] + sum(row_heights[:r]) + row_heights[r] +  + row_start
                    y -= self.cell_padding[3]
                else:
                    raise ValueError(f"Invalid anchor: {cell.anchor}")
                if cell.bg_color:
                    draw.rectangle(
                        (x - self.cell_padding[0],
                         y + self.cell_padding[1],
                         x + col_widths[c] + self.cell_padding[2],
                         y + row_heights[r] + self.cell_padding[3]), fill=cell.bg_color)
                draw.text((x, y), cell.text, font=cell.font, fill=cell.color, anchor=cell.anchor)

        # Draw lines

        for r in self.h_lines:
            y = xy[1] + sum(row_heights[:r])
            draw.line((xy[0], y, xy[0] + sum(col_widths), y), fill=self.table_color)
        total_height = sum(row_heights)
        for c, col in enumerate(col_widths):
            if c == 0:
                continue
            x = xy[0] + col_starts[c]
            draw.line((x, xy[1], x, xy[1] + total_height), fill=self.table_color)
