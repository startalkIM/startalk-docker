--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/5/5
-- Time: 下午4:30
-- To change this template use File | Settings | File Templates.
--

local _M = {}
function _M:ckeyCheck()

    local _CheckRet = {}
    _CheckRet.httpcode = 200
    _CheckRet.bizcode = 0
    _CheckRet.retmessage = ""

    local inArgs = ngx.req.get_uri_args()
    local inCkey = ngx.var.cookie_q_ckey;

    if nil== inCkey then
        local qcookiesHelper = require("checks.qcookiehelper")
        local ckeyCheckResult = qcookiesHelper:QCookieParse()
        inCkey = ckeyCheckResult["q_ckey"];

    end

    if nil == inCkey then
        local responce = require("utils.http_responce")
        _CheckRet.retmessage = "ckey is need";
        _CheckRet.bizcode = 5000
        ngx.log(ngx.ERR, "e " .. "ckey is need")
        return _CheckRet
    else
        local decodedCkeyString = ngx.decode_base64(inCkey)

        if nil == decodedCkeyString then
            _CheckRet.retmessage = "ckey is decode fail";
            _CheckRet.bizcode = 5000
            ngx.log(ngx.ERR, "e " .. "ckey is decode fail")
            return _CheckRet
        end



        require("utils.string_ex")
        local params = decodedCkeyString:split("&")
        local decodedCkey = {}

        for i=1 ,#params do
            local subparam = params[i]
            local kv = subparam:split("=")
            if 2 == #kv then
                decodedCkey[kv[1]] = kv[2]
            end
        end

        -- 客户端版本问题，这里暂时不判定t
        if nil == decodedCkey["u"] or nil == decodedCkey["k"] then
            local responce = require("utils.http_responce")
            _CheckRet.retmessage = "ckey is parse wrong";
            _CheckRet.bizcode = 5000
            ngx.log(ngx.ERR, "e " .. "ckey is parse wrong")
            return _CheckRet
        end

        local config = require("checks.qim.qtalkredis")
        local user = decodedCkey["u"]
        local t    = decodedCkey["t"]
        local key  = decodedCkey["k"]


        if nil == t then
            t = ""
        end

        -- 从redis 里拿出来 u 这个人的 key
        local redis = require "resty.redis"
        local red = redis:new()
        red:set_timeout(500)


        local  ok, err = red:connect(config.redis.host, config.redis.port)
        --connect redis ok
        if ok then
            ok, err = red:auth(config.redis.passwd)

            red:select(tonumber(config.redis.subpool))

            if ok then
                ok, err = red:hkeys(user)

                if ok then
                    local checkpass = false
                    for k,v in pairs(ok) do
                        local newkey = string.upper(ngx.md5(v .. t))
                        if newkey == key then
                            checkpass = true
                            break
                        end
                    end


                    if not checkpass then
                        _CheckRet.retmessage = "ckey is wrong";
                        _CheckRet.bizcode = 5000
                        ngx.log(ngx.ERR, "e " .. "ckey is wrong")
                        return _CheckRet
                    end
                else
                    local responce = require("utils.http_responce")

                    _CheckRet.retmessage = "check fail";
                    _CheckRet.bizcode = 5000
                    ngx.log(ngx.ERR, "e " .. "check fail")
                    return _CheckRet
                end
            else
                local responce = require("utils.http_responce")
                _CheckRet.retmessage = "redis auth fail " .. err;
                _CheckRet.bizcode = 5000

                ngx.log(ngx.ERR, "e " .. "redis auth fail " .. err)

                return _CheckRet
            end
        else
            local responce = require("utils.http_responce")
            _CheckRet.retmessage = "failed to connnect redis:" .. err;
            _CheckRet.bizcode = 5000
            ngx.log(ngx.ERR, "e " .. "failed to connnect redis:" .. err)
            return _CheckRet
        end
    end
    return _CheckRet;
end

return _M
