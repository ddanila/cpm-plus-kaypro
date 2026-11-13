/* SPDX-License-Identifier: MIT. Timed serial/PTY harness; never injects RAM. */
#define _POSIX_C_SOURCE 200809L
#include "machines/kaypro2/kaypro2.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t stop;
static void stopped(int s){(void)s;stop=1;}
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
static void tx(void *p,unsigned n,uint8_t v){if(n==0&&write(*(int*)p,&v,1)!=1)stop=1;}
int main(int argc,char **argv){
 if(argc!=4&&argc!=5)return 2;
 int keyboard=argc==5?atoi(argv[4]):-1;
 if(keyboard>=0)fcntl(keyboard,F_SETFL,fcntl(keyboard,F_GETFL)|O_NONBLOCK);
 int fd=atoi(argv[2]);kaypro2 *m=calloc(1,sizeof(*m));if(!m)return 2;kaypro2_init(m);
 FILE *f=fopen(argv[1],"rb");uint8_t rom[4096];
 if(!f||fread(rom,1,4096,f)!=4096||fgetc(f)!=EOF)return 2;
 fclose(f);
 if(kaypro2_load(m,rom,4096))return 2;
 const char *fontpath=getenv("KAYPRO_CHARGEN");uint8_t font[2048]={0};
 if(fontpath){
  FILE *ff=fopen(fontpath,"rb");
  if(!ff||fread(font,1,sizeof font,ff)!=sizeof font||fgetc(ff)!=EOF)return 2;
  fclose(ff);
 }else{
  /* Explicit synthetic renderer fixture, not historical character shapes. */
  for(unsigned c=128;c<256;c++)for(unsigned y=0;y<8;y++)font[c*8+y]=(c+y*3)&31;
 }
 if(kaypro2_load_chargen(m,font,sizeof font))return 2;
 uint8_t *floppy[2]={NULL,NULL}; const char *floppy_paths[2]={getenv("KAYPRO_FLOPPY_C"),getenv("KAYPRO_FLOPPY_D")};
 for(unsigned i=0;i<2;i++)if(floppy_paths[i]){
  floppy[i]=malloc(204800);FILE *df=fopen(floppy_paths[i],"rb");
  if(!floppy[i]||!df||fread(floppy[i],1,204800,df)!=204800||fgetc(df)!=EOF)return 2;
  fclose(df);if(kaypro2_mount(m,i,dac_memory_storage(floppy[i],204800,1),getenv("KAYPRO_FLOPPY_RO")==NULL))return 2;
 }
 m->serial_user=&fd;m->transmit=tx;
 fcntl(fd,F_SETFL,fcntl(fd,F_GETFL)|O_NONBLOCK);
 signal(SIGTERM,stopped);signal(SIGINT,stopped);
 unsigned service=getenv("KAYPRO_KEYSERVICE")?(unsigned)strtoul(getenv("KAYPRO_KEYSERVICE"),NULL,0):0;
 unsigned boot_sync=getenv("KAYPRO_BOOT_SYNC")?(unsigned)strtoul(getenv("KAYPRO_BOOT_SYNC"),NULL,0):0;
 unsigned last_boot_state=~0u;
 uint64_t last_service=0,max_gap=0,last_key=0;unsigned prior_pc=0;
 uint64_t start=ns(),next_rx=0,next_key=0,report=0;unsigned dropped=0,key_dropped=0,key_received=0;
 unsigned reset_drops=0;int reset_trial=getenv("KAYPRO_RESET_TRIAL")!=NULL;int runtime_seen=!reset_trial;
 while(!stop){
  uint64_t target=(ns()-start)*KAYPRO2_CLOCK_HZ/1000000000u;
  if(target>m->cpu.cycles+25000)target=m->cpu.cycles+25000;
  while(m->cpu.cycles<target){
   if(m->cpu.cycles>=next_rx){uint8_t b;ssize_t n=read(fd,&b,1);
    if(n==1){if(kaypro2_receive(m,0,b)){dropped++;if(!runtime_seen)reset_drops++;fprintf(stderr,"rx-drop pc=%04x runtime=%d\n",m->cpu.cpu.pc,runtime_seen);}
     unsigned ticks=kaypro2_character_ticks(m,0);next_rx=m->cpu.cycles+(ticks?ticks:1303);}
    else if(n<0&&errno!=EAGAIN&&errno!=EINTR&&errno!=EIO)stop=1;
   }
   if(keyboard>=0&&m->cpu.cycles>=next_key){uint8_t b;ssize_t n=read(keyboard,&b,1);
    if(n==1){if(kaypro2_receive(m,1,b))key_dropped++;else key_received++;last_key=m->cpu.cycles;
     next_key=m->cpu.cycles+83334; /* independent 300 baud 8N1 source */}
   }
   if(last_key&&m->cpu.cycles-last_key<=250000){
    if(service&&m->cpu.cpu.pc==service&&prior_pc!=service){
     if(last_service&&m->cpu.cycles-last_service>max_gap)max_gap=m->cpu.cycles-last_service;
     last_service=m->cpu.cycles;
    }
   }else last_service=0;
   /* Read-only observation at the ROM input loop, never register/RAM injection. */
   if(boot_sync && m->cpu.cpu.pc==boot_sync){
    unsigned state=((unsigned)m->ram[0x9002]<<16)|((unsigned)m->ram[0x9000]<<8)|m->ram[0x9001];
    if(state!=last_boot_state){
     fprintf(stderr,"monitor-ready mode=%u selector=%u wr4=%02x\n",m->ram[0x9002],m->ram[0x9000],m->ram[0x9001]);
     last_boot_state=state;
    }
   }
   if(m->cpu.cpu.pc==0xc033)runtime_seen=1;
   prior_pc=m->cpu.cpu.pc;
   kaypro2_run(m,1);
  }
  if(m->cpu.cycles>=report){fprintf(stderr,"pc=%04x bank=%02x baud=%u wr4=%02x dropped=%u\n",m->cpu.cpu.pc,m->system,kaypro2_baud(m,0),m->sio[0].wr[4],dropped);report+=KAYPRO2_CLOCK_HZ*5u;}
  struct timespec delay={0,100000};nanosleep(&delay,NULL);
 }
 f=fopen(argv[3],"wb");if(f){fwrite(m->ram,1,65536,f);fclose(f);}
 fprintf(stderr,"final pc=%04x dropped=%u unclaimed=%llu\n",m->cpu.cpu.pc,dropped,(unsigned long long)m->unclaimed_io);
 char path[4096];
 if(snprintf(path,sizeof path,"%s.video.bin",argv[3])>0){f=fopen(path,"wb");if(f){fwrite(m->video,1,2048,f);fclose(f);}}
 if(snprintf(path,sizeof path,"%s.screen.bin",argv[3])>0){f=fopen(path,"wb");if(f){
  for(unsigned y=0;y<24;y++)for(unsigned x=0;x<80;x++)fputc(m->video[kaypro2_video_index(0x3000+y*128+x)],f);
  fclose(f);}}
 if(snprintf(path,sizeof path,"%s.screen.pgm",argv[3])>0){f=fopen(path,"wb");if(f){
  uint8_t *pixels=malloc(560*240);if(!pixels)return 2;
  kaypro2_render(m,pixels,1);fprintf(f,"P5\n# font=%s\n560 240\n1\n",fontpath?"external":"synthetic");
  fwrite(pixels,1,560*240,f);free(pixels);fclose(f);}}
 fprintf(stderr,"keyboard received=%u dropped=%u max_service_gap=%llu\n",key_received,key_dropped,(unsigned long long)max_gap);
 fprintf(stderr,"reset-transition-drops=%u runtime-drops=%u\n",reset_drops,dropped-reset_drops);
 for(unsigned i=0;i<2;i++)if(floppy[i]){
  if(!getenv("KAYPRO_FLOPPY_RO")){f=fopen(floppy_paths[i],"wb");if(!f||fwrite(floppy[i],1,204800,f)!=204800)return 2;fclose(f);}
  free(floppy[i]);
 }
 free(m);return dropped-reset_drops||key_dropped?1:0;
}
