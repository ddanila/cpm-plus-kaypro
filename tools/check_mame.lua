-- Independent startup check using the SAME custom EPROM, no RAM injection.
local count=0
emu.register_frame_done(function()
 count=count+1
 if count==30 then
  local cpu=manager.machine.devices[':maincpu']
  local mem=cpu.spaces['program']
  local pc=cpu.state['PC'].value
  local relocated=mem:read_u8(0x8000)==0x3e and mem:read_u8(0x8001)==0x40
  mem:write_u8(0x100,0x5a)
  local ram=mem:read_u8(0x100)==0x5a
  local ok=relocated and ram and pc>=0x8000 and pc<0x8100
  print(string.format('KAYPRO_STARTUP {"pass":%s,"pc":%d,"relocated":%s,"low_ram":%s}',tostring(ok),pc,tostring(relocated),tostring(ram)))
  manager.machine:exit()
 end
end,'kaypro_startup')
