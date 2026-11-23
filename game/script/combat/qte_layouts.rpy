init -5 python:
    def qte_layout_grid(count, x, y, spread, randomize):
        columns = math.ceil(math.sqrt(count))
        rows = math.ceil(count / columns)

        sx, sy= spread

        return [
            (
                x if columns == 1 else (x - sx / 2 + (i % columns) * sx / (columns - 1)),
                y if rows == 1 else (y - sy / 2 + (i // columns) * sy / (rows - 1)),
            ) for i in range(count)
        ]
    
    def qte_layout_line(count, x, y, spread, randomize):
        if count == 1:
            return [(x, y)]
        
        sx, sy = spread

        return [
            (
                x + (i / (count - 1) - 0.5) * sx,
                y + (i / (count - 1) - 0.5) * sy,
            ) for i in range(count)
        ]
    
    def qte_layout_fixed(count, x, y, spread, randomize):
        return [(x, y)] * count

    def qte_layout_random(count, x, y, spread, randomize):
        sx, sy = spread

        qte_require(0 <= x - sx / 2 <= x + sx / 2 <= 1 and 0 <= y - sy / 2 <= y + sy / 2 <= 1, "Random layout spread exceeds the screne resolution")

        if not randomize:
            return [(x, y)] * count

        return [
            (
                renpy.random.uniform(x - sx / 2, x + sx / 2),
                renpy.random.uniform(y - sy / 2, y + sy / 2),
            ) for _ in range(count)
        ]
    
    QTE_LAYOUTS = {
        "grid": qte_layout_grid,
        "line": qte_layout_line,
        "fixed": qte_layout_fixed,
        "random": qte_layout_random,
    }

    def qte_layout_points(step, count, randomize=False):
        name = step.get("layout", "grid")
        spread = step.get("spread", (0.6, 0.4))

        qte_require(isinstance(name, str) and name in QTE_LAYOUTS, 
                    "Unknown QTE Layout received, got: %r\nList of available layouts: %r" % (name, list(QTE_LAYOUTS)))
        qte_require(isinstance(spread, (builtins.list, tuple)) and len(spread) == 2 and all(qte_number(v) and 0 <= v <= 1 for v in spread), 
                    "Spread needs two numbers from 0 to 1, instead got: %r" % (spread,))

        return QTE_LAYOUTS[name](count, step.get("x", 0.5), step.get("y", 0.6), spread, randomize)
