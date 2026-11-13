-- Independent controller cross-check: no replacement controller code here.
local count=0
local lost=nil
emu.register_frame_done(function()
 count=count+1
 local io=manager.machine.devices[':maincpu'].spaces['io']
 if count==30 then io:write_u8(0x1c,0x01) end
 if count==65 then
  io:write_u8(0x11,0);io:write_u8(0x12,0);io:write_u8(0x10,0x80)
 end
 if count==80 then
  lost=io:read_u8(0x10)
  io:write_u8(0x10,0xd0)
 end
 if count==81 then
  io:write_u8(0x12,10);io:write_u8(0x10,0x80)
 end
 if count==150 then
  local missing=io:read_u8(0x10)
  local ok=(lost&4)~=0 and (lost&1)==0 and (missing&16)~=0 and (missing&1)==0
  print(string.format('KAYPRO_FDC {"pass":%s,"lost_data_status":%d,"missing_sector_status":%d}',tostring(ok),lost,missing))
  manager.machine:exit()
 end
end,'kaypro_fdc')
