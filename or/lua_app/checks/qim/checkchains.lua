--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/5/5
-- Time: 下午4:30
-- To change this template use File | Settings | File Templates.
--
-- 检查ckey
local ckeyChecker = require("checks.qim.ckeycheck")

local ckeyCheckResult = ckeyChecker:ckeyCheck()
if 0 ~= ckeyCheckResult.bizcode then
    local responce = require("utils.http_responce")
    local result = responce.failResponce(ckeyCheckResult.bizcode, ckeyCheckResult.retmessage, "")
    ngx.log(ngx.ERR, " ckeycheck error " .. result)
    ngx.say(result)
    ngx.exit(ckeyCheckResult.httpcode)
end


local bodytimes = require("checks.qim.bodytimes")
local limitCheckResult = bodytimes:checkLimtied()
if 0~= limitCheckResult.bizcode then
    local responce = require("utils.http_responce")
    local result = responce.failResponce(limitCheckResult.bizcode,limitCheckResult.retmessage,"")
    ngx.log(ngx.ERR, " bodytimes error " .. result)
    ngx.say(result)
    ngx.exit(limitCheckResult.httpcode)
end









