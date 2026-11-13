-- MIT. Read the physical CRT memory after 20 emulated seconds of stock boot.
local frames=0
emu.register_frame_done(function()
 frames=frames+1
 if frames==1200 then
  local cpu=manager.machine.devices[':maincpu']
  local mem=cpu.spaces['program']
  print('STOCK_PC '..cpu.state['PC'].value)
  cpu.spaces['io']:write_u8(0x1c,0xc1)
  for row=0,23 do
   local line=''
   for col=0,79 do
    local c=mem:read_u8(0x3000+row*128+col)%128
    line=line..string.char(c>=32 and c<127 and c or 32)
   end
   print(line)
  end
  manager.machine:exit()
 end
end,'stock_boot')
