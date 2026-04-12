-- grd-crossref.lua
--
-- Pandoc Lua filter: resolve namespaced wikilink-style cross-references into
-- LaTeX \ref{} commands.
--
--   [[phase:3]]     -> \ref{phase:3}
--   [[eq:euler]]    -> \ref{eq:euler}
--   [[fig:conv]]    -> Figure~\ref{fig:conv}   (namespace-specific prefix)
--   [[tab:results]] -> Table~\ref{tab:results}
--   [[sec:intro]]   -> Section~\ref{sec:intro}
--
-- Domain-agnostic: the namespaces are a convention, not physics-specific.
-- GRD uses "phase:" for workflow phases; GPD could add "chapter:". Other
-- projects (like the originating OSB setup) only care about eq/fig/tab/sec.
--
-- Configuration via document metadata:
--   crossref_namespaces: list[str]
--     Which namespaces to intercept. Default: phase, eq, fig, tab, sec,
--     appendix.
--   crossref_prefix.<ns>: str
--     Per-namespace LaTeX text printed before \ref{}. Use an empty string
--     to emit just \ref{...} with no prefix.
--
-- Filter ordering: run this BEFORE citeproc so our bracket syntax does not
-- collide with pandoc's @-citation handling. Crossref uses wikilink-style
-- brackets, citeproc uses @keys -- they don't actually overlap, but keeping
-- crossref earlier matches the mental model.


local DEFAULT_NAMESPACES = { "phase", "eq", "fig", "tab", "sec", "appendix" }
local DEFAULT_PREFIXES = {
  eq = "",                -- \ref alone is conventional for equations in most journals
  fig = "Figure~",
  tab = "Table~",
  sec = "Section~",
  appendix = "Appendix~",
  phase = "",
}

local namespaces = {}
local prefixes = {}

local function build_namespace_pattern()
  -- Anchored "word" group for Lua patterns -- Lua doesn't support alternation,
  -- so we match any letters and check membership after.
  return "%[%[([%a][%w]*):([^%[%]]+)%]%]"
end

local function is_known(ns)
  for _, n in ipairs(namespaces) do
    if n == ns then return true end
  end
  return false
end

local function prefix_for(ns)
  if prefixes[ns] ~= nil then return prefixes[ns] end
  return DEFAULT_PREFIXES[ns] or ""
end

local function render_ref(ns, id)
  local p = prefix_for(ns)
  return p .. "\\ref{" .. ns .. ":" .. id .. "}"
end

-- Treat any ipairs-iterable metadata value as a list (MetaList or pandoc List).
local function iter_meta_list(value)
  if value == nil then return nil end
  if type(value) ~= "table" then return nil end
  local has_items = false
  for _ in ipairs(value) do has_items = true; break end
  if not has_items then return nil end
  return value
end

function Meta(meta)
  namespaces = {}
  local list = iter_meta_list(meta.crossref_namespaces)
  if list then
    for _, entry in ipairs(list) do
      namespaces[#namespaces+1] = pandoc.utils.stringify(entry)
    end
  else
    for _, n in ipairs(DEFAULT_NAMESPACES) do namespaces[#namespaces+1] = n end
  end

  prefixes = {}
  if meta.crossref_prefix and type(meta.crossref_prefix) == "table" then
    for key, value in pairs(meta.crossref_prefix) do
      -- Skip metadata framework fields (t, tag) that pandoc attaches.
      if key ~= "t" and key ~= "tag" then
        prefixes[key] = pandoc.utils.stringify(value)
      end
    end
  end

  -- Consume our config keys.
  meta.crossref_namespaces = nil
  meta.crossref_prefix = nil
  return meta
end

-- Walk an inlines list, find [[ns:id]] sequences, and replace with raw LaTeX
-- \ref{...}. We operate on the stringified run to tolerate pandoc's
-- fragmentation across Str/Space tokens.
function Inlines(inlines)
  local out = {}
  local i = 1
  while i <= #inlines do
    local el = inlines[i]
    if el.t == "Str" then
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
      local rewrote = false
      local pat = build_namespace_pattern()
      while pos <= #text do
        local s, e, ns, id = text:find(pat, pos)
        if not s then break end
        if not is_known(ns) then
          -- Not our namespace -- skip past the match and keep looking.
          pos = e + 1
        else
          if not rewrote and s > 1 then
            -- Emit any prefix text only once we know there's a match.
          end
          if s > pos then
            out[#out+1] = pandoc.Str(text:sub(pos, s - 1))
          end
          out[#out+1] = pandoc.RawInline("latex", render_ref(ns, id:gsub("^%s+", ""):gsub("%s+$", "")))
          pos = e + 1
          rewrote = true
        end
      end
      if rewrote then
        if pos <= #text then
          out[#out+1] = pandoc.Str(text:sub(pos))
        end
      else
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

return {
  { Meta = Meta },
  { Inlines = Inlines },
}
