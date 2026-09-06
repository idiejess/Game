class_name UITheme
extends RefCounted
## Builds the game Theme from the Art Bible palette. Supports text scale and high contrast.

const POUND_GREEN := Color("#0F2E2B")
const WET_SLATE := Color("#2B3A42")
const LAMP_AMBER := Color("#E0A33A")
const CHALK := Color("#EDE6D6")
const INK := Color("#1A1714")
const REED_OCHRE := Color("#8C6B2F")
const CHARTER_GREEN := Color("#3F7D5A")
const ALDMERE_BLUE := Color("#3B5F8A")
const SORREL_RUST := Color("#B4482B")
const CHAPEL_BLUE := Color("#7C8FA6")
const TOWN_BRICK := Color("#9C5A3C")
const DANGER_RED := Color("#C8352E")

const RESOURCE_COLORS := {
	"water": ALDMERE_BLUE, "traffic": SORREL_RUST, "coffers": LAMP_AMBER, "company": CHARTER_GREEN, "town": TOWN_BRICK,
}
const RESOURCE_GLYPHS := {"water": "≈", "traffic": "⇄", "coffers": "▣", "company": "§", "town": "♀"}

const BASE_FONT := 34
const SMALL_FONT := 26
const TITLE_FONT := 56


## Font size honouring the player's text-size setting, for controls that override theme sizes.
static func scaled(px: int) -> int:
	return int(round(px * float(Settings.get_value("text_scale"))))


static func build(text_scale: float, high_contrast: bool) -> Theme:
	var t := Theme.new()
	var base := int(BASE_FONT * text_scale)
	var small := int(SMALL_FONT * text_scale)
	var title := int(TITLE_FONT * text_scale)
	t.default_font_size = base
	var fg := Color.WHITE if high_contrast else CHALK
	var panel_bg := Color.BLACK if high_contrast else WET_SLATE
	var accent := Color("#FFD24D") if high_contrast else LAMP_AMBER

	t.set_color("font_color", "Label", fg)
	t.set_font_size("font_size", "Label", base)
	t.set_color("font_color", "Button", fg)
	t.set_color("font_hover_color", "Button", accent)
	t.set_color("font_focus_color", "Button", accent)
	t.set_color("font_pressed_color", "Button", INK)
	t.set_font_size("font_size", "Button", base)
	t.set_color("default_color", "RichTextLabel", fg)
	t.set_font_size("normal_font_size", "RichTextLabel", base)
	t.set_font_size("font_size", "LineEdit", base)
	t.set_color("font_color", "LineEdit", fg)
	t.set_color("font_color", "CheckButton", fg)
	t.set_font_size("font_size", "CheckButton", base)
	t.set_font_size("font_size", "OptionButton", base)

	var btn := docket_box(panel_bg, accent if high_contrast else Color(0, 0, 0, 0), 2 if high_contrast else 0)
	t.set_stylebox("normal", "Button", btn)
	t.set_stylebox("hover", "Button", docket_box(panel_bg.lightened(0.12), accent, 2))
	t.set_stylebox("pressed", "Button", docket_box(accent, accent, 2))
	t.set_stylebox("focus", "Button", docket_box(Color(0, 0, 0, 0), accent, 4))
	t.set_stylebox("disabled", "Button", docket_box(panel_bg.darkened(0.3), Color(0, 0, 0, 0), 0))
	t.set_stylebox("panel", "PanelContainer", docket_box(panel_bg, accent if high_contrast else Color(0, 0, 0, 0), 2 if high_contrast else 0))
	t.set_stylebox("normal", "LineEdit", docket_box(INK, accent, 2))
	t.set_stylebox("focus", "LineEdit", docket_box(INK, accent, 4))
	t.set_constant("h_separation", "HBoxContainer", int(16 * text_scale))
	t.set_constant("separation", "VBoxContainer", int(14 * text_scale))
	t.set_font_size("font_size", "TitleLabel", title)
	t.set_type_variation("TitleLabel", "Label")
	t.set_color("font_color", "TitleLabel", accent)
	t.set_type_variation("SmallLabel", "Label")
	t.set_font_size("font_size", "SmallLabel", small)
	t.set_color("font_color", "SmallLabel", fg.darkened(0.15))
	return t


## Rounded box with one square corner (the "docket" corner).
static func docket_box(bg: Color, border: Color, border_w: int, radius: int = 18) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.set_corner_radius_all(radius)
	s.corner_radius_top_right = 0
	s.border_color = border
	s.set_border_width_all(border_w)
	s.content_margin_left = 28
	s.content_margin_right = 28
	s.content_margin_top = 18
	s.content_margin_bottom = 18
	return s


static func faction_color(faction: String) -> Color:
	match faction:
		"company": return CHARTER_GREEN
		"town": return TOWN_BRICK
		"hullfolk": return REED_OCHRE
		"aldmere": return ALDMERE_BLUE
		"sorrel": return SORREL_RUST
		"concordance": return CHAPEL_BLUE
	return CHAPEL_BLUE
