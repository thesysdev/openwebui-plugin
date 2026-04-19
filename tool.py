"""
title: OpenUI - Generative UI
author: thesysdev/vishxrad
version: 0.4.0
description: Renders interactive generative UI components (charts, forms, tables, cards, follow-ups) in chat using OpenUI Lang.
"""

import json

from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse


# ---------------------------------------------------------------------------
# Theme detection script - runs in <head> before content renders so CSS
# variables resolve to the correct theme immediately.
# ---------------------------------------------------------------------------

_THEME_SCRIPT = """<script>
(function() {
  function detectTheme(root) {
    return root.classList.contains('dark')
      || root.getAttribute('data-theme') === 'dark'
      || getComputedStyle(root).colorScheme === 'dark';
  }
  function applyTheme(isDark) {
    var t = isDark ? 'dark' : 'light';
    if (document.documentElement.getAttribute('data-theme') === t) return;
    document.documentElement.setAttribute('data-theme', t);
  }
  try {
    var p = parent.document.documentElement;
    applyTheme(detectTheme(p));
    new MutationObserver(function() {
      applyTheme(detectTheme(p));
    }).observe(p, { attributes: true, attributeFilter: ['class', 'data-theme', 'style'] });
  } catch(e) {
    var mq = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');
    if (mq) {
      applyTheme(mq.matches);
      mq.addEventListener('change', function(e) { applyTheme(e.matches); });
    }
  }
})();
</script>"""


# ---------------------------------------------------------------------------
# Body scripts - height reporting, sendPrompt bridge, openLink, render
# ---------------------------------------------------------------------------

_BODY_SCRIPTS = """<script>
var _rhLast = 0;
var _rhRaf = 0;

function reportHeight() {
  var saved = document.body.style.cssText;
  document.body.style.setProperty('height', 'auto', 'important');
  document.body.style.setProperty('overflow', 'visible', 'important');
  var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
  document.body.style.cssText = saved;
  if (h === _rhLast) return;
  _rhLast = h;
  parent.postMessage({ type: 'iframe:height', height: h }, '*');
}

window.addEventListener('load', function() {
  reportHeight();
  setTimeout(reportHeight, 200);
  setTimeout(reportHeight, 1000);
  setTimeout(reportHeight, 3000);
});
new ResizeObserver(function() {
  cancelAnimationFrame(_rhRaf);
  _rhRaf = requestAnimationFrame(reportHeight);
}).observe(document.body);
new MutationObserver(function() {
  cancelAnimationFrame(_rhRaf);
  _rhRaf = requestAnimationFrame(reportHeight);
}).observe(document.body, { childList: true, subtree: true });
window.addEventListener('resize', reportHeight);
document.addEventListener('toggle', function() {
  _rhLast = 0;
  setTimeout(reportHeight, 50);
}, true);

function sendPrompt(text) {
  try {
    parent.postMessage({ type: 'input:prompt:submit', text: text }, '*');
  } catch(e) {}
}

function openLink(url) {
  try { parent.window.open(url, '_blank'); }
  catch(e) { window.open(url, '_blank'); }
}
</script>"""


_CDN_BASE = "https://cdn.jsdelivr.net/npm/@vishxrad/openui-webui-bundle@0.1.0"


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------

def _build_openui_html(code: str, title: str = "Response", cdn_base: str = _CDN_BASE) -> str:
    safe_title = (
        title.replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;")
    )
    code_json = json.dumps(code)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title}</title>
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; connect-src https://cdn.jsdelivr.net; img-src * data: blob:; font-src 'self' data: https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self'">
<link rel="stylesheet" href="{cdn_base}/openui-styles.css">
<style>
* {{ box-sizing: border-box; margin: 0; }}
html, body {{ background: transparent; }}
body {{ padding: 4px; overflow: visible; }}
#openui-root {{ width: 100%; }}
.openui-loading {{
  display: flex; align-items: center; justify-content: center;
  padding: 32px; color: #888; font-family: system-ui, -apple-system, sans-serif;
  font-size: 14px;
}}
.openui-error {{
  padding: 16px; color: #dc2626; font-family: system-ui, sans-serif;
  background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;
  font-size: 13px; line-height: 1.5;
}}
.openui-error strong {{ display: block; margin-bottom: 4px; }}
</style>
{_THEME_SCRIPT}
</head>
<body>
<div id="openui-root"><div class="openui-loading">Loading components&#8230;</div></div>
{_BODY_SCRIPTS}
<script>
(function() {{
  var script = document.createElement('script');
  script.src = '{cdn_base}/openui-bundle.min.js';
  script.onload = function() {{
    try {{
      var OpenUI = window.__OpenUI;
      if (!OpenUI || !OpenUI.Renderer || !OpenUI.openuiChatLibrary) {{
        throw new Error('OpenUI bundle loaded but exports missing');
      }}

      var code = {code_json};
      var container = document.getElementById('openui-root');
      container.innerHTML = '';

      var root = OpenUI.createRoot(container);

      function handleAction(event) {{
        if (event.type === 'open_url') {{
          openLink(event.params && event.params.url ? event.params.url : '');
          return;
        }}

        var prompt = event.humanFriendlyMessage || (event.params && event.params.message) || '';

        if (event.formState && Object.keys(event.formState).length > 0) {{
          var formDataStr = Object.entries(event.formState)
            .map(function(entry) {{ return entry[0] + ': ' + JSON.stringify(entry[1]); }})
            .join('\\n');
          prompt = prompt
            ? prompt + '\\n\\nForm data:\\n' + formDataStr
            : 'Form submission' + (event.formName ? ' (' + event.formName + ')' : '') + ':\\n' + formDataStr;
        }}

        if (!prompt && event.type) {{
          prompt = 'User action: ' + event.type + (event.params ? '\\n' + JSON.stringify(event.params) : '');
        }}

        if (prompt) {{
          sendPrompt(prompt);
        }}
      }}

      root.render(OpenUI.React.createElement(OpenUI.Renderer, {{
        response: code,
        library: OpenUI.openuiChatLibrary,
        isStreaming: false,
        onAction: handleAction
      }}));

      setTimeout(reportHeight, 500);
      setTimeout(reportHeight, 2000);
    }} catch(err) {{
      var el = document.getElementById('openui-root');
      el.innerHTML = '<div class="openui-error"><strong>Failed to render OpenUI</strong>'
        + (err.message || String(err)).replace(/</g, '&lt;') + '</div>';
      console.error('OpenUI render error:', err);
      reportHeight();
    }}
  }};
  script.onerror = function() {{
    var el = document.getElementById('openui-root');
    el.innerHTML = '<div class="openui-error"><strong>Failed to load OpenUI bundle</strong>'
      + 'Could not load ' + script.src + '. Make sure openui-bundle.min.js is in the static directory.</div>';
    reportHeight();
  }};
  document.body.appendChild(script);
}})();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Tool class
# ---------------------------------------------------------------------------

class Tools:
    """OpenUI Generative UI - renders interactive components in chat.

    When the user's question could benefit from a visual response (charts,
    tables, forms, cards, step lists, follow-ups, etc.), call render_openui
    to render a rich interactive UI instead of plain markdown.

    NEVER output openui-lang code as text. ALWAYS pass it to render_openui.
    """

    class Valves(BaseModel):
        cdn_base_url: str = Field(
            default=_CDN_BASE,
            description="Base CDN URL for the OpenUI bundle. Change if self-hosting or using a different version.",
        )

    def __init__(self):
        self.valves = self.Valves()

    async def render_openui(
        self,
        openui_lang_code: str,
        title: str = "Response",
        __event_emitter__=None,
    ) -> tuple:
        """
        Render interactive UI components inline in the chat using OpenUI Lang.
        Use this tool whenever a visual response would be helpful: tables, charts,
        forms, lists, cards, step guides, follow-up suggestions, etc.

        IMPORTANT: Pass the openui-lang code as the openui_lang_code argument.
        NEVER output openui-lang as text in your response. After calling this tool,
        briefly describe what the user sees - do NOT echo the source code.

        ## OpenUI Lang Syntax

        Each statement: `identifier = Expression`. `root = Card(...)` is the entry point.
        Expressions: strings ("..."), numbers, booleans, null, arrays ([...]), objects ({...}), or TypeName(arg1, arg2, ...).
        Arguments are POSITIONAL. Write TypeName(arg1, arg2) NOT TypeName(key: val).
        Every variable (except root) must be referenced by another. Unreferenced = not rendered.

        ## Components

        Card(children[]) - root container, children stack vertically.
        CardHeader(title?, subtitle?)
        TextContent(text, size?) - size: "small"|"default"|"large"|"small-heavy"|"large-heavy"
        MarkDownRenderer(textMarkdown, variant?) - variant: "clear"|"card"|"sunk"
        Callout(variant, title, description) - variant: "info"|"warning"|"error"|"success"|"neutral"
        TextCallout(variant?, title?, description?)
        Image(alt, src?)
        ImageBlock(src, alt?)
        ImageGallery(images[{src,alt?,details?}])
        CodeBlock(language, codeString)
        Separator(orientation?, decorative?)

        Table(columns: Col[])
        Col(label, data[], type?) - type: "string"|"number"|"action"

        BarChart(labels[], series: Series[], variant?, xLabel?, yLabel?) - variant: "grouped"|"stacked"
        LineChart(labels[], series: Series[], variant?, xLabel?, yLabel?) - variant: "linear"|"natural"|"step"
        AreaChart(labels[], series: Series[], variant?, xLabel?, yLabel?)
        HorizontalBarChart(labels[], series: Series[], variant?, xLabel?, yLabel?)
        RadarChart(labels[], series: Series[])
        Series(category, values[])

        PieChart(labels[], values[], variant?) - variant: "pie"|"donut"
        RadialChart(labels[], values[])
        SingleStackedBarChart(labels[], values[])

        ScatterChart(datasets: ScatterSeries[], xLabel?, yLabel?)
        ScatterSeries(name, points: Point[])
        Point(x, y, z?)

        Form(name, buttons: Buttons, fields?: FormControl[])
        FormControl(label, input, hint?)
        Input(name, placeholder?, type?, rules?, value?)
        TextArea(name, placeholder?, rows?, rules?, value?)
        Select(name, items: SelectItem[], placeholder?, rules?, value?)
        SelectItem(value, label)
        DatePicker(name, mode?, rules?, value?)
        Slider(name, variant, min, max, step?, defaultValue?, label?, rules?, value?)
        CheckBoxGroup(name, items: CheckBoxItem[], rules?, value?)
        CheckBoxItem(label, description, name, defaultChecked?)
        RadioGroup(name, items: RadioItem[], defaultValue?, rules?, value?)
        RadioItem(label, description, value)
        SwitchGroup(name, items: SwitchItem[], variant?, value?)
        SwitchItem(label?, description?, name, defaultChecked?)

        Button(label, action?, variant?, type?, size?) - variant: "primary"|"secondary"|"tertiary"
        Buttons(buttons[], direction?) - direction: "row"|"column"

        ListBlock(items: ListItem[], variant?) - variant: "number"|"image"
        ListItem(title, subtitle?, image?, actionLabel?, action?)
        FollowUpBlock(items: FollowUpItem[]) - clickable follow-ups at end
        FollowUpItem(text) - clicking sends text as user message

        SectionBlock(sections: SectionItem[], isFoldable?)
        SectionItem(value, trigger, content[])

        Tabs(items: TabItem[])
        TabItem(value, trigger, content[])
        Accordion(items: AccordionItem[])
        AccordionItem(value, trigger, content[])
        Steps(items: StepsItem[])
        StepsItem(title, details)
        Carousel(children[][], variant?) - each slide is array of components; all slides same structure

        TagBlock(tags[])
        Tag(text, icon?, size?, variant?)

        Action([@steps...]) - wires buttons. Steps: @ToAssistant("msg"), @OpenUrl("url")
        Buttons without Action auto-send their label.

        ## Examples

        Table: root = Card([title, tbl, followUps])
        title = TextContent("Top Languages", "large-heavy")
        tbl = Table([Col("Language", langs), Col("Users (M)", users)])
        langs = ["Python", "JavaScript", "Java"]
        users = [15.7, 14.2, 12.1]
        followUps = FollowUpBlock([FollowUpItem("Tell me more about Python")])

        Chart: root = Card([header, chart])
        header = CardHeader("Monthly Revenue")
        chart = BarChart(months, [Series("Revenue", values)])
        months = ["Jan", "Feb", "Mar", "Apr"]
        values = [42000, 51000, 48000, 62000]

        Form: root = Card([title, form])
        title = TextContent("Contact Us", "large-heavy")
        form = Form("contact", btns, [nameField, emailField])
        nameField = FormControl("Name", Input("name", "Your name", "text", {required: true}))
        emailField = FormControl("Email", Input("email", "you@example.com", "email", {required: true, email: true}))
        btns = Buttons([Button("Submit", Action([@ToAssistant("Submit")]), "primary")])

        ## Rules
        - root = Card(...) MUST be the FIRST line.
        - Every name must be defined and reachable from root.
        - Card is the only layout container. Do NOT use Stack.
        - Use FollowUpBlock at the END for next actions.
        - Carousel slides MUST all have the same structure.
        - Generate realistic data when asked about data.

        :param openui_lang_code: Complete OpenUI Lang code starting with root = Card(...)
        :param title: Short descriptive title for the rendered UI.
        :return: Interactive rich embed rendered inline in the chat.
        """
        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Rendering \"{title}\"...",
                        "done": False,
                    },
                }
            )

        response = HTMLResponse(
            content=_build_openui_html(openui_lang_code, title, self.valves.cdn_base_url),
            headers={"Content-Disposition": "inline"},
        )

        if __event_emitter__:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Rendered \"{title}\"",
                        "done": True,
                    },
                }
            )
        result_context = (
            f'OpenUI visualization "{title}" is now rendered and visible to the '
            f"user as an interactive embed. DO NOT echo back the OpenUI Lang source "
            f"code. Instead, briefly describe what the visualization shows in plain "
            f"language. If the visualization has interactive elements (clickable items, "
            f"buttons, forms, follow-ups), mention what the user can interact with."
        )
        return response, result_context
