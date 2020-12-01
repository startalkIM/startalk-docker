--
-- Created by IntelliJ IDEA.
-- User: qitmac000378
-- Date: 17/7/6
-- Time: 下午4:30
-- To change this template use File | Settings | File Templates.
--

local _M = {}
function _M:array_item_exit(array,item)
    if "table" ~= type(array) then
        return false
    end

    for i = 1, #array do
        if item == array[i] then
            return true
        end
    end
    return false
end

return _M

