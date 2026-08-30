"""Visual projections of existing optimizer results; no evaluation or ranking."""

from __future__ import annotations

import json
from pathlib import Path

ASSETS = Path(__file__).with_name("assets")
BG = "#F2F5F4"
INK = "#173831"
MUTED = "#596B65"
ACCENT = "#116B55"
METRICS = {"power": "Power", "control": "Control", "spin": "Spin",
           "bounce_reduction_percent": "Bounce Reduction", "wind_resistance_percent": "Wind Resistance",
           "groundspin_increase_percent": "Groundspin", "loft_angle_degrees": "Loft",
           "groundspin": "Groundspin", "swing_speed": "Swing Speed",
           "gravity_reduction_percent": "Gravity Reduction",
           "launch_angle_degrees": "Launch Angle", "fade_draw_multiplier": "Fade/Draw"}
ROLES = {"active": "Actif", "support": "Support", "hybrid": "Actif + support", "neutral": "Sans effet observé"}
SECONDARY_AXES = ("bounce_reduction_percent", "wind_resistance_percent")


def number(value):
    return "—" if value is None else f"{value:g}"


def metric_label(metric):
    return METRICS.get(metric, metric.replace("_", " "))


def unit(metric):
    return " %" if metric.endswith("_percent") else "°" if metric.endswith("_degrees") else ""


def step_labels_for(strategy):
    """Short presentation labels derived from the declared shot sequence."""
    labels = {}
    for index, step in enumerate(strategy.sequence):
        if step.function.identifier == "finish":
            label = "Putt"
        elif index == 0:
            label = "Attaque du green" if step.function.identifier == "reach_target_zone" else "Départ"
        else:
            label = "Approche" if step.function.identifier == "reach_target_zone" else step.name
        labels[step.identifier] = label
    return labels


def display_step(club):
    """Active clubs use their own shot; supports use the first evaluated shot.

    The shot label always accompanies these values: there is no invented
    scenario-independent final value and no fallback to base stats.
    """
    return next((step for step in club.steps if step.step_id in club.active_steps),
                club.steps[0] if club.steps else None)


def club_projection(club, candidate, step_labels):
    step = display_step(club)
    names = {item.club_id: item.club_name for item in candidate.clubs}
    reasons = []
    axis_reasons = []
    for evaluated in club.steps:
        active_target = candidate.active_assignments.get(evaluated.step_id)
        for contribution in evaluated.contributions_sent:
            if contribution.target_club_id != active_target:
                continue
            for metric, value in contribution.modification.items():
                if value:
                    destination = axis_reasons if metric in SECONDARY_AXES and (
                        evaluated.metric_relevance.get(metric) == "objective"
                    ) else reasons
                    destination.append(
                        f"{value:+g}{unit(metric)} {metric_label(metric)} → "
                        f"{names.get(contribution.target_club_id, contribution.target_club_id)}"
                        f" · {step_labels.get(evaluated.step_id, evaluated.step_id)}"
                    )
    reasons = list(dict.fromkeys((*axis_reasons, *reasons)))
    unresolved = tuple(dict.fromkeys(item for evaluated in club.steps for item in evaluated.unresolved_abilities))
    return {
        "id": club.club_id, "name": club.club_name, "type": club.club_type,
        "level": "?" if club.level is None else str(club.level), "position": club.position,
        "role": ROLES.get(club.role, club.role),
        "step": step_labels.get(step.step_id, step.step_id) if step else "Non évalué",
        "stats": {metric: number(step.final_stats.get(metric)) if step else "—"
                  for metric in ("power", "control", "spin")},
        "reasons": tuple(reasons), "unresolved": unresolved,
    }


def metric_changes(candidate, step_labels):
    """Keep positive/negative changes separate, without assigning desirability."""
    changes = []
    for key, delta in (candidate.metric_deltas_from_power_max or {}).items():
        if delta == 0:
            continue
        step, _, metric = key.partition(".")
        if metric in SECONDARY_AXES:
            active = getattr(candidate, "active_assignments", {}).get(step)
            evaluated = next((shot for club in getattr(candidate, "clubs", ()) if club.club_id == active
                              for shot in club.steps if shot.step_id == step), None)
            if evaluated is None or evaluated.metric_relevance.get(metric) != "objective":
                continue
        if delta is None:
            if metric in SECONDARY_AXES:
                changes.append(f"{metric_label(metric)} : écart indéterminé · {step_labels.get(step, step)}")
            continue
        suffix = " points de %" if metric.endswith("_percent") else unit(metric)
        changes.append(f"{delta:+g}{suffix} {metric_label(metric)} · {step_labels.get(step, step)}")
    return tuple(changes)


def secondary_summary(step, *, complete):
    """Only active comparison axes; missing values in partial bags stay unknown."""
    if step is None:
        return ()
    return tuple(
        f"{metric_label(metric)} {number(step.additional_metrics.get(metric, 0 if complete else None))} %"
        for metric in SECONDARY_AXES if step.metric_relevance.get(metric) == "objective"
    )


def secondary_cautions(step):
    """Surface additive-model limits without inventing a stacking rule."""
    if step is None:
        return ()
    return tuple(
        f"{metric_label(metric)} : plusieurs sources additionnées ; cumul en jeu à valider."
        for metric in SECONDARY_AXES
        if step.metric_relevance.get(metric) == "objective"
        and len({(item.source_club_id, item.ability_id) for item in step.contributions_received
                 if item.modification.get(metric)}) > 1
    )


class GraphicAssets:
    def __init__(self, root, catalog, directory=ASSETS):
        self.root, self.directory = root, Path(directory)
        self.brands = {key: club["brand"]["name"] for key, club in catalog["clubs"].items()}
        try:
            self.colors = {row["brand"]: row["color_start"] for row in json.loads(
                (self.directory / "brand_colors.json").read_text(encoding="utf-8"))}
        except (OSError, ValueError, KeyError, TypeError):
            self.colors = {}
        self.photos = {}

    def color(self, club_id):
        value = self.colors.get(self.brands.get(club_id), "#526862")
        return value if isinstance(value, str) and len(value) == 7 and value.startswith("#") and all(c in "0123456789abcdefABCDEF" for c in value[1:]) else "#526862"

    def photo(self, club_id):
        import tkinter as tk
        if club_id not in self.photos:
            try:
                # Identifiers come from the catalogue; still disallow path traversal.
                if Path(club_id).name != club_id or "\\" in club_id:
                    return None
                self.photos[club_id] = tk.PhotoImage(master=self.root, file=str(self.directory / "club_icons" / f"{club_id}.png"))
            except (tk.TclError, OSError):
                self.photos[club_id] = None
        return self.photos[club_id]


class ScrollArea:
    """Independent vertical scrolling, including keyboard and Windows wheel."""
    def __init__(self, parent, *, background=BG):
        import tkinter as tk
        from tkinter import ttk
        self.frame = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.frame, bg=background, highlightthickness=0, takefocus=True)
        bar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=background)
        self.window = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.window, width=e.width))
        self.canvas.bind("<Next>", lambda _: self.canvas.yview_scroll(1, "pages"))
        self.canvas.bind("<Prior>", lambda _: self.canvas.yview_scroll(-1, "pages"))
        # App-level binding dispatches only events originating within this area.
        self._wheel_id = parent.winfo_toplevel().bind("<MouseWheel>", self._wheel, add="+")
        self.frame.bind("<Destroy>", self._dispose, add="+")

    def _dispose(self, event):
        if event.widget == self.frame:
            self.frame.winfo_toplevel().unbind("<MouseWheel>", self._wheel_id)

    def _wheel(self, event):
        widget = event.widget
        while widget is not None:
            if widget == self.frame:
                self.canvas.yview_scroll(-int(event.delta / 120), "units")
                return "break"
            widget = getattr(widget, "master", None)


def render_cards(parent, result, presentation, assets, step_labels, on_detail, on_save):
    import tkinter as tk
    from tkinter import ttk

    for child in parent.winfo_children():
        child.destroy()

    def label(host, text, *, size=10, bold=False, fg=INK, bg="white", **kw):
        item = tk.Label(host, text=text, bg=bg, fg=fg, font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w", justify="left", **kw)
        return item

    if not result.retained_results:
        label(parent, "Aucun sac retenu avec ces contraintes.\nEssayez de relâcher un minimum ou un filtre de marque.", bg=BG, size=13).pack(padx=20, pady=30)
    cards = []
    for index, candidate in enumerate(result.retained_results):
        card = tk.Frame(parent, bg="white", highlightbackground="#D8E2DC", highlightthickness=1)
        card.pack(fill="x", padx=16, pady=(0, 16))
        cards.append(card)
        heading = tk.Frame(card, bg="white")
        heading.pack(fill="x", padx=18, pady=(14, 6))
        title = presentation.candidates[index].families or "Proposition retenue"
        if candidate.optimization_badges:
            title = " · ".join(candidate.optimization_badges).capitalize()
        label(heading, f"{index + 1:02}  {title}", size=14, bold=True, wraplength=600).pack(side="left")
        ttk.Button(heading, text="Détail technique ↗", command=lambda i=index: on_detail(i)).pack(side="right")
        unresolved = len(candidate.unresolved_abilities)
        if unresolved:
            label(card, f"Partiellement évalué · {unresolved} capacité(s) non résolue(s)", fg="#805119", size=9).pack(fill="x", padx=18, pady=(0, 4))
        changes = metric_changes(candidate, step_labels)
        delta_label = label(card, " / ".join(changes) if changes else "Point de comparaison : puissance maximale trouvée" if "power_max" in candidate.result_family_ids else "Pas d’écart chiffré disponible",
                            fg=MUTED, wraplength=900)
        delta_label.pack(fill="x", padx=18, pady=(0, 3))
        delta_label.bind("<Configure>", lambda event: event.widget.configure(wraplength=max(120, event.width - 4)))
        if changes:
            label(card, "Écarts par rapport au sac « puissance maximale trouvée »", size=9, fg=MUTED).pack(fill="x", padx=18)
        summary = tk.Frame(card, bg="#EAF2EE")
        summary.pack(fill="x", padx=18, pady=(10, 12))
        for column, (step_id, club_id) in enumerate(candidate.active_assignments.items()):
            club = next(item for item in candidate.clubs if item.club_id == club_id)
            step = next((item for item in club.steps if item.step_id == step_id), None)
            summary.columnconfigure(column, weight=1, uniform="steps")
            text = f"{step_labels.get(step_id, step_id)}\n{club.club_name}"
            stats = "  ·  ".join(f"{METRICS[metric]} {number(step.final_stats.get(metric)) if step else '—'}" for metric in ("power", "control", "spin"))
            secondary = secondary_summary(step, complete=not candidate.unresolved_abilities)
            if secondary:
                stats += "\n" + "\n".join(secondary)
            label(summary, text + "\n" + stats, bold=True, size=10, bg="#EAF2EE", wraplength=280).grid(row=0, column=column, sticky="nw", padx=12, pady=10)
            cautions = secondary_cautions(step)
            if cautions:
                label(summary, "\n".join(cautions), size=9, fg="#805119", bg="#EAF2EE", wraplength=280).grid(row=1, column=column, sticky="nw", padx=12, pady=(0, 8))
        tiles = tk.Frame(card, bg="white", name="clubs")
        tiles.pack(fill="x", padx=12)
        for column, club in enumerate(candidate.clubs):
            data = club_projection(club, candidate, step_labels)
            tiles.columnconfigure(column, weight=1, uniform="clubs")
            tile = tk.Frame(tiles, bg="white", highlightbackground="#E5EBE7", highlightthickness=1, name=f"club_{column + 1}")
            tile.grid(row=0, column=column, sticky="nsew", padx=4)
            stripe = assets.color(club.club_id)
            tk.Frame(tile, bg=stripe, height=4).pack(fill="x")
            label(tile, f"{club.position:02}  {data['role']}", size=9, fg=MUTED, wraplength=150, height=2).pack(fill="x", padx=8, pady=(8, 0))
            photo = assets.photo(club.club_id)
            if photo:
                tk.Label(tile, image=photo, bg="white").pack(pady=3)
            else:
                label(tile, club.club_name[:2].upper(), size=28, bold=True, fg=stripe, height=2).pack(pady=3)
            label(tile, club.club_name, bold=True, size=11, wraplength=155, height=2).pack(fill="x", padx=8)
            label(tile, f"{club.club_type.title()} · Niv. {data['level']}", size=9, fg=MUTED).pack(fill="x", padx=8)
            stats = tk.Frame(tile, bg="#F3F6F4")
            stats.pack(fill="x", padx=6, pady=8)
            for col, (metric, value) in enumerate(data["stats"].items()):
                stats.columnconfigure(col, weight=1, uniform="stats")
                tk.Label(stats, text=value, bg="#F3F6F4", fg=INK, font=("Segoe UI", 17, "bold")).grid(row=0, column=col, sticky="ew")
                tk.Label(stats, text=METRICS[metric], bg="#F3F6F4", fg=MUTED, font=("Segoe UI", 8)).grid(row=1, column=col, sticky="ew")
            label(tile, f"Finales · {data['step']}", fg=MUTED, size=8, wraplength=155).pack(fill="x", padx=8)
            reasons = list(data["reasons"][:2])
            if len(data["reasons"]) > 2:
                reasons.append(f"+ {len(data['reasons']) - 2} contributions dans le détail")
            if data["unresolved"]:
                reasons.append("Effet potentiel non résolu")
            label(tile, "\n".join(reasons) or data["role"], size=9, fg=MUTED, wraplength=170).pack(fill="x", padx=8, pady=(8, 12))
        actions = tk.Frame(card, bg="white")
        actions.pack(fill="x", padx=18, pady=12)
        label(actions, "Valeurs calculables · — = indisponible", size=9, fg=MUTED).pack(side="left")
        ttk.Button(actions, text="Enregistrer ce sac", command=lambda i=index: on_save(i)).pack(side="right", padx=8)
    return cards
