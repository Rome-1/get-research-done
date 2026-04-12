-- grd-obsidian-compat.lua
--
-- Pandoc Lua filter: make Obsidian-flavoured markdown behave when pandoc
-- converts it to LaTeX. Superset of OSB's obsidian-compat.lua -- handles
-- wikilinks, callouts, and Obsidian-specific YAML metadata.
--
-- Domain-agnostic: no physics / GRD / GPD-specific logic. The same filter
-- is reusable in any project that drafts in Obsidian markdown and renders
-- to LaTeX. The `grd-` prefix reflects the ship-from-GRD history only.
--
-- Configuration via document metadata (all optional):
--   obsidian_strip_fields:   list[str]  extra YAML fields to strip
--   obsidian_wikilink_style: "text" or "ref"  how to render wikilink
--                                             targets (default: "text")


-- Default set of Obsidian-specific metadata fields to remove so they don't
-- leak into the LaTeX preamble.
local DEFAULT_STRIP_FIELDS = {
  "type", "kb_type", "kb_collection", "status", "decay",
  "last_verified", "tags", "aliases", "cssclass", "publish",
}

-- State set by Meta() at document start.
local wikilink_style = "text"
local strip_fields = {}

local function contains(list, value)
  for _, v in ipairs(list) do
    if v == value then return true end
  end
  return false
end

-- Convert a markdown wikilink target like "Folder/Note#heading" into a clean
-- LaTeX-safe reference key. Lowercase, alnum + hyphen + colon.
local function normalise_ref(target)
  local tail = target:match("[^/]+$") or target
  tail = tail:lower():gsub("%s+", "-"):gsub("[^%w%-:]", "")
  if tail == "" then tail = "ref" end
  return tail
end

local function render_wikilink(target, display)
  display = display or (target:match("[^/]+$") or target)
  if wikilink_style == "ref" then
    -- Emit raw LaTeX so it survives further AST traversal unchanged.
    return pandoc.RawInline("latex", "\\ref{" .. normalise_ref(target) .. "}")
  end
  return pandoc.Str(display)
end

-- Pandoc tokenises "[[target|display]]" into several Inline elements (Str,
-- Str, etc.), so operating on a single Str is insufficient for reliable
-- rewriting. We walk Inlines and rebuild runs that contain wikilinks.
function Inlines(inlines)
  local out = {}
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    if el.t == "Str" then
      -- Re-serialise a span of consecutive inlines back into text so we can
      -- regex-match wikilinks that pandoc split across tokens.
      local start = i
      local buf = {}
      while i <= #inlines and (inlines[i].t == "Str" or inlines[i].t == "Space" or inlines[i].t == "SoftBreak") do
        if inlines[i].t == "Str" then
          buf[#buf+1] = inlines[i].text
        else
          buf[#buf+1] = " "
        end
        i = i + 1
      end
      local text = table.concat(buf)
      local pos = 1
      local has_wikilink = false
      while pos <= #text do
        local s, e, target, display = text:find("%[%[([^%[%]|]+)|([^%[%]]+)%]%]", pos)
        local bare_s, bare_e, bare = text:find("%[%[([^%[%]|]+)%]%]", pos)
        local match_s, match_e, match_target, match_display
        if s and (not bare_s or s <= bare_s) then
          match_s, match_e, match_target, match_display = s, e, target, display
        elseif bare_s then
          match_s, match_e, match_target, match_display = bare_s, bare_e, bare, nil
        else
          break
        end
        has_wikilink = true
        if match_s > pos then
          out[#out+1] = pandoc.Str(text:sub(pos, match_s - 1))
        end
        out[#out+1] = render_wikilink(match_target, match_display)
        pos = match_e + 1
      end
      if has_wikilink then
        if pos <= #text then
          out[#out+1] = pandoc.Str(text:sub(pos))
        end
      else
        -- No wikilinks in this run -- put the originals back untouched.
        for j = start, i - 1 do
          out[#out+1] = inlines[j]
        end
      end
    else
      out[#out+1] = el
      i = i + 1
    end
  end
  return out
end

-- Convert Obsidian callouts like "> [!note] Title\n> body" into a bold label
-- followed by the body content inside the existing BlockQuote. The callout
-- marker and title live on the first line (before a SoftBreak); the body is
-- every inline after that SoftBreak.
function BlockQuote(el)
  if #el.content == 0 then return nil end
  local first = el.content[1]
  if first.t ~= "Para" or #first.content == 0 then return nil end

  -- Collect inlines up to (but not including) the first SoftBreak/LineBreak.
  local header_inlines = {}
  local rest_inlines = {}
  local in_rest = false
  for _, node in ipairs(first.content) do
    if not in_rest and (node.t == "SoftBreak" or node.t == "LineBreak") then
      in_rest = true
    elseif in_rest then
      rest_inlines[#rest_inlines + 1] = node
    else
      header_inlines[#header_inlines + 1] = node
    end
  end

  local header = pandoc.utils.stringify(pandoc.Inlines(header_inlines))
  local callout_type, title = header:match("^%[!(%w+)%]%s*(.*)$")
  if not callout_type then return nil end

  local label = callout_type:sub(1, 1):upper() .. callout_type:sub(2):lower()
  if title and title ~= "" then
    label = label .. ": " .. title
  end
  local bold = pandoc.Para({ pandoc.Strong({ pandoc.Str(label) }) })
  if #rest_inlines > 0 then
    el.content[1] = pandoc.Para(rest_inlines)
    table.insert(el.content, 1, bold)
  else
    el.content[1] = bold
  end
  return el
end

-- Strip Obsidian-specific metadata so it doesn't break the LaTeX preamble.
function Meta(meta)
  -- Read configuration before we start mutating.
  if meta.obsidian_wikilink_style then
    wikilink_style = pandoc.utils.stringify(meta.obsidian_wikilink_style)
  end
  strip_fields = {}
  for _, f in ipairs(DEFAULT_STRIP_FIELDS) do strip_fields[#strip_fields+1] = f end
  if meta.obsidian_strip_fields and meta.obsidian_strip_fields.t == "MetaList" then
    for _, entry in ipairs(meta.obsidian_strip_fields) do
      local name = pandoc.utils.stringify(entry)
      if name ~= "" and not contains(strip_fields, name) then
        strip_fields[#strip_fields+1] = name
      end
    end
  end
  for _, field in ipairs(strip_fields) do
    meta[field] = nil
  end
  -- Consume our own configuration keys so they don't bleed into templates.
  meta.obsidian_strip_fields = nil
  meta.obsidian_wikilink_style = nil
  return meta
end

-- Ordering: Meta must run first so wikilink_style is set before Inlines.
return {
  { Meta = Meta },
  { Inlines = Inlines, BlockQuote = BlockQuote },
}
