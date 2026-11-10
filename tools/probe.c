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
 if(argc!=4)return 2;
 int fd=atoi(argv[2]);kaypro2 *m=calloc(1,sizeof(*m));if(!m)return 2;kaypro2_init(m);
 FILE *f=fopen(argv[1],"rb");uint8_t rom[4096];
 if(!f||fread(rom,1,4096,f)!=4096||fgetc(f)!=EOF)return 2;fclose(f);
 if(kaypro2_load(m,rom,4096))return 2;
 m->serial_user=&fd;m->transmit=tx;
 fcntl(fd,F_SETFL,fcntl(fd,F_GETFL)|O_NONBLOCK);
 signal(SIGTERM,stopped);signal(SIGINT,stopped);
 uint64_t start=ns(),next_rx=0,report=0;unsigned dropped=0;
 while(!stop){
  uint64_t target=(ns()-start)*KAYPRO2_CLOCK_HZ/1000000000u;
  if(target>m->cpu.cycles+25000)target=m->cpu.cycles+25000;
  while(m->cpu.cycles<target){
   if(m->cpu.cycles>=next_rx){uint8_t b;ssize_t n=read(fd,&b,1);
    if(n==1){if(kaypro2_receive(m,0,b))dropped++;
     unsigned ticks=kaypro2_character_ticks(m,0);next_rx=m->cpu.cycles+(ticks?ticks:1303);}
    else if(n<0&&errno!=EAGAIN&&errno!=EINTR&&errno!=EIO)stop=1;
   }
   kaypro2_run(m,1);
  }
  if(m->cpu.cycles>=report){fprintf(stderr,"pc=%04x bank=%02x baud=%u wr4=%02x dropped=%u\n",m->cpu.cpu.pc,m->system,kaypro2_baud(m,0),m->sio[0].wr[4],dropped);report+=KAYPRO2_CLOCK_HZ*5u;}
  struct timespec delay={0,100000};nanosleep(&delay,NULL);
 }
 f=fopen(argv[3],"wb");if(f){fwrite(m->ram,1,65536,f);fclose(f);}
 fprintf(stderr,"final pc=%04x dropped=%u unclaimed=%llu\n",m->cpu.cpu.pc,dropped,(unsigned long long)m->unclaimed_io);
 free(m);return dropped?1:0;
}
