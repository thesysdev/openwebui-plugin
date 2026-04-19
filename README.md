# OpenUI Generative UI Tool for Open WebUI

An [Open WebUI](https://github.com/open-webui/open-webui) tool that renders interactive generative UI components (charts, forms, tables, cards, follow-ups) in chat using [OpenUI](https://www.openui.com/) Lang.

## How it works

1. The LLM calls `render_openui(openui_lang_code, title)` with OpenUI Lang code
2. The tool builds a self-contained HTML page that loads the OpenUI renderer + component library from CDN
3. Open WebUI renders it as an inline iframe embed
4. User interactions (follow-up clicks, form submissions, buttons) post back into chat via `sendPrompt`

## Installation

### Option A: From openwebui.com (recommended)

Visit the tool page on [openwebui.com/tools](https://openwebui.com/tools) and import directly.

### Option B: Manual

1. Go to **Admin > Tools** in your Open WebUI instance
2. Click **+** to create a new tool
3. Paste the contents of [`openui_tool.py`](openui_tool.py)
4. Save

That's it. No other setup needed — the JS bundle and CSS are loaded from CDN automatically.

## Usage

Enable the tool in a chat (click the tools icon next to the message input). Then ask questions that would benefit from visual responses:

- "Show me a comparison table of the top 5 programming languages"
- "Create a bar chart of monthly revenue"
- "Build a contact form with name, email, and message"
- "Give me a step-by-step guide to setting up Docker"

The model will call `render_openui` and the UI will appear inline in the chat.

## Components available

The tool supports 40+ components from the OpenUI chat library:

- **Content**: TextContent, CardHeader, MarkDownRenderer, Callout, CodeBlock, Image, ImageGallery
- **Charts**: BarChart, LineChart, AreaChart, PieChart, RadarChart, ScatterChart, HorizontalBarChart, RadialChart
- **Tables**: Table with typed columns
- **Forms**: Form, Input, TextArea, Select, DatePicker, Slider, CheckBoxGroup, RadioGroup, SwitchGroup
- **Layout**: Tabs, Accordion, Carousel, SectionBlock, Steps
- **Interactive**: Button, ListBlock, FollowUpBlock (sends follow-up as user message)

## Architecture

```
openui_tool.py          Python tool (paste into Open WebUI Admin > Tools)
bundle/
  openui-entry.js       esbuild entry point
  package.json          npm deps for rebuilding the bundle
```

The tool loads a pre-built browser bundle from CDN (`@vishxrad/openui-webui-bundle`) which contains React, the OpenUI parser/renderer, and the full component library (recharts, radix-ui, etc.) in a single IIFE file.

## Rebuilding the bundle

If you need to rebuild (e.g., to use a newer OpenUI version):

```bash
cd bundle
npm install
npx esbuild openui-entry.js --bundle --format=iife --minify --outfile=openui-bundle.min.js --define:process.env.NODE_ENV=\"production\" --target=es2020
```

## Configuration

The tool has one Valve (configurable in Admin > Tools):

- **cdn_base_url**: Base CDN URL for the OpenUI bundle. Defaults to `https://cdn.jsdelivr.net/npm/@vishxrad/openui-webui-bundle@0.1.0`. Change if self-hosting or using a different version.

## Limitations

- **No streaming**: Tools execute after the LLM finishes generating the tool call arguments. The UI renders all at once, not token-by-token. This is a fundamental limitation of the tool/plugin architecture.
- **Bundle size**: The first load fetches ~650KB (gzipped) from CDN. Subsequent loads are cached by the browser.

## License

MIT
