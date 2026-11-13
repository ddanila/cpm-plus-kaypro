/* MIT. Driver unit-test adapter; RAM loading here is NOT boot qualification. */
#include "machines/kaypro2/kaypro2.h"
#include <stdlib.h>
#include <string.h>
kaypro2 *board_new(void){kaypro2 *m=calloc(1,sizeof(*m));if(m)kaypro2_init(m);return m;}
void board_free(kaypro2 *m){free(m);}
void board_load(kaypro2 *m,unsigned a,const void *p,unsigned n){if(a+n<=65536)memcpy(m->ram+a,p,n);}
unsigned board_peek(kaypro2 *m,unsigned a){return m->ram[a&65535];}
void board_poke(kaypro2 *m,unsigned a,unsigned v){m->ram[a&65535]=v;}
unsigned board_cell(kaypro2 *m,unsigned row,unsigned col){return m->video[kaypro2_video_index(0x3000+row*128+col)];}
unsigned board_bank(kaypro2 *m){return m->system;}
unsigned board_receive(kaypro2 *m,unsigned n,unsigned v){return kaypro2_receive(m,n,v);}
unsigned board_baud(kaypro2 *m,unsigned n){return kaypro2_baud(m,n);}
unsigned board_error(kaypro2 *m,unsigned n){return m->sio[n].errors;}
unsigned long long board_cycles(kaypro2 *m){return m->cpu.cycles;}
static unsigned key_stream, key_sent;
void board_key_stream(kaypro2 *m,unsigned n){(void)m;key_stream=n;key_sent=0;}
static int call_limited(kaypro2 *m,unsigned addr,unsigned bc,unsigned sp,unsigned limit){
 uint8_t code[]={0x31,sp&255,sp>>8,0x01,bc&255,bc>>8,0xcd,addr&255,addr>>8,0x76};
 memcpy(m->ram+0x4000,code,sizeof code);
 m->cpu.pins=z80_prefetch(&m->cpu.cpu,0x4000);m->io_active=0;
 for(unsigned i=0;i<limit;i++){
  if(key_sent<key_stream && i%83334==0){kaypro2_receive(m,1,65+(key_sent%26));key_sent++;}
  kaypro2_run(m,1);
  if((m->cpu.pins&Z80_HALT) && (m->cpu.cpu.pc==0x400a || m->cpu.cpu.pc==1)){key_stream=0;return m->cpu.cpu.a;}
 }
 return -1;
}
static unsigned ntx;static uint8_t txdata[32768];
static void capture(void *p,unsigned ch,uint8_t v){(void)p;if(ch==0&&ntx<sizeof txdata)txdata[ntx++]=v;}
int board_rom(kaypro2 *m,const void *p,unsigned n){ntx=0;m->transmit=capture;return kaypro2_load(m,p,n);}
void board_tick(kaypro2 *m,unsigned n){kaypro2_run(m,n);}
unsigned board_tx(kaypro2 *m,void *p){(void)m;memcpy(p,txdata,ntx);unsigned n=ntx;ntx=0;return n;}
unsigned board_pc(kaypro2 *m){return m->cpu.cpu.pc;}

int board_call(kaypro2 *m,unsigned addr,unsigned bc){return call_limited(m,addr,bc,0xf700,2000000);}
unsigned board_receive_status(kaypro2 *m,unsigned n,unsigned v,unsigned errors){return kaypro2_receive_status(m,n,v,errors);}
void board_modem(kaypro2 *m,unsigned n,unsigned bits){kaypro2_modem(m,n,bits);}
unsigned board_wr(kaypro2 *m,unsigned n,unsigned r){return m->sio[n&1].wr[r&7];}

int board_mount(kaypro2 *m,unsigned drive,void *bytes,unsigned size,unsigned writable){return kaypro2_mount(m,drive,dac_memory_storage(bytes,size,writable),writable);}
void board_eject(kaypro2 *m,unsigned drive){kaypro2_eject(m,drive);}
void board_fault(kaypro2 *m,unsigned drive,unsigned status){m->floppy_fault[drive&1]=status;}
unsigned board_fdc(kaypro2 *m,unsigned reg){return reg==4?m->fdc.lost_position:wd179x_read(&m->fdc,reg);}

int board_call_stack(kaypro2 *m,unsigned addr,unsigned bc,unsigned sp){return call_limited(m,addr,bc,sp,2000000);}
int board_call_floppy(kaypro2 *m,unsigned addr,unsigned bc){return call_limited(m,addr,bc,0xf700,12000000);}
