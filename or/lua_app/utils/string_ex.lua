--------------------------- Lua字符串分隔方法 -----------------------------------------
function string:split(sep)
    local sep, fields = sep or ":", {}
    local pattern = string.format("([^%s]+)", sep)
    self:gsub(pattern, function (c) fields[#fields + 1] = c end)
    return fields
end
--------------------------- Lua字符串分隔方法 -----------------------------------------