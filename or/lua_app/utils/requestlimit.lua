--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/7/6
-- Time: 下午2:18
-- To change this template use File | Settings | File Templates.
--

#!/usr/bin/lua

local config = require("config")
local ip = ngx.var.remote_addr
local cookie_qn1 = ngx.var.cookie_QN1
local port = ngx.var.server_port
local url = ngx.var.scheme .. '://' .. ngx.var.host .. ":" .. port .. ngx.var.request_uri
local encode_url = ngx.escape_uri(ngx.encode_base64(url))
local ip_key = ''
local rkey = ''
if cookie_qn1 == nil then
    ip_key = ip .. ":num"
    rkey = ip .. ":banned"
else
    ip_key = ip .. ":" .. cookie_qn1 .. ":num"
    rkey = ip .. ":" .. cookie_qn1 .. ":banned"
end

ngx.log(ngx.ERR, "ip key:", ip_key)
ngx.log(ngx.ERR, "rkey:", rkey)

local redis = require "resty.redis"
local red = redis:new()
red:set_timeout(500)

local  ok, err = red:connect(config.redis.host, config.redis.port)
--connect redis ok
if ok then
    ok, err = red:auth(config.redis.passwd)
else
    ngx.log(ngx.ERR, "failed to connnect redis:", err)
end
--auth ok
if ok then
    ok, err = red:get(rkey)

    -- redis get value ok
    if ok then
        if tonumber(ok) == 1 then
            ngx.log(ngx.ERR, "ip {" .. rkey .."} is in black list, type is 1")
            return ngx.exit(403)
        elseif tonumber(ok) == 2 then
            ngx.log(ngx.ERR, "ip {" .. rkey .."} is in black list, type is 2")
            ngx.exec("/captcha?url=" .. encode_url)
            return
        end
    else
        ngx.log(ngx.ERR, "failed to get ", rkey ,": ", err)
    end

    -- ip access rate
    local  req, err = red:get(ip_key)

    if req ~= ngx.null then
        ngx.log(ngx.ERR, "req is not null",req)
        if tonumber(req) > 9 then
            ok, err = red:set(rkey, 2)
            if ok then
                red:expire(rkey, 600)
                ngx.exec("/captcha?url=" .. encode_url)
            else
                ngx.log(ngx.ERR, "failed to set ",rkey ,": ", err)
            end
        else
            red:incr(ip_key)
        end
    else
        ngx.log(ngx.ERR, "req is null")
        red:set(ip_key,1)
        red:expire(ip_key, 60)
        req = 1
    end

    --redis pool
    ok, err = red:set_keepalive(1000, 100)
    if not ok then
        ngx.log(ngx.ERR, "failed to set keepalive: ", err)
    end
else
    ngx.log(ngx.ERR, "failed to authenticate: ", err)
end
