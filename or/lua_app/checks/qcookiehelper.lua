--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/5/5
-- Time: 下午5:42
-- To change this template use File | Settings | File Templates.
--

local _M = {}
function _M:QCookieParse()
    local h = ngx.req.get_headers()
    local kvpair = {}
    for k, v in pairs(h) do
        if k=="qcookie" then
            if nil ~= v then
                require("utils.string_ex")
                local params = v:split(";")
                for i=1 ,#params do
                    local subparam = params[i]

                    local kv = subparam:split("=")
                    if 2 == #kv then
                        kvpair[kv[1]] = kv[2]
                    end
                end
            end
            break;
        end
    end

    return kvpair
end

return _M;