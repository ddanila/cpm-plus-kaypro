-- Same replacement EPROM, independent CPU/PIO/SIO/video implementation.
local count=0
emu.register_frame_done(function()
 count=count+1
 if count==30 then
  local cpu=manager.machine.devices[':maincpu']
  local mem=cpu.spaces['program']
  local io=cpu.spaces['io']
  local pc=cpu.state['PC'].value
  local relocated=mem:read_u8(0x8000)==0x3e and mem:read_u8(0x8001)==0x40
  mem:write_u8(0x100,0x5a)
  local ram=mem:read_u8(0x100)==0x5a
  -- Inspect video via real bank register, then restore it before further ticks.
  io:write_u8(0x1c,0xc0)
  local text=''
  for i=0,28 do text=text..string.char(mem:read_u8(0x3000+i)) end
  io:write_u8(0x1c,0x40)
  local banner=text=='Kaypro serial boot ROM v3.0.0'
  local ok=relocated and ram and banner and pc>=0x8000 and pc<0x9000
  print(string.format('KAYPRO_STARTUP {"pass":%s,"pc":%d,"relocated":%s,"low_ram":%s,"crt_banner":%s}',tostring(ok),pc,tostring(relocated),tostring(ram),tostring(banner)))
  manager.machine:exit()
 end
end,'kaypro_startup')
