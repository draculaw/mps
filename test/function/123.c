/* 
TEST_HEADER
 id = $Id$
 summary = regression test for AWl bug (request.dylan.160094
 language = c
 link = testlib.o rankfmt.o
END_HEADER
*/

#include "testlib.h"
#include "mpscawl.h"
#include "mpscamc.h"
#include "mpsavm.h"
#include "rankfmt.h"

void *stackpointer;

mycell *a, *b;

static void test(void)
{
 mps_arena_t arena;
 mps_pool_t poolamc, poolawl;
 mps_thr_t thread;
 mps_root_t root, rootb;

 mps_fmt_t format;
 mps_ap_t apamc, apawl;

 unsigned int i, c;

 cdie(mps_arena_create(&arena, mps_arena_class_vm(), (size_t) (60ul*1024*1024)), "create arena");

 cdie(mps_thread_reg(&thread, arena), "register thread");

 cdie(mps_root_create_table(&root, arena, mps_rank_ambig(), 0, &b, 1),
  "creat root");

 cdie(mps_root_create_table(&rootb, arena, mps_rank_ambig(), 0, &exfmt_root, 1),
  "create root b");

 cdie(
  mps_fmt_create_A(&format, arena, &fmtA),
  "create format");

 cdie(
  mps_pool_create(&poolamc, arena, mps_class_amc(), format),
  "create pool");

 cdie(
  mps_pool_create(&poolawl, arena, mps_class_awl(), format),
  "create pool");

 cdie(
  mps_ap_create(&apawl, poolawl, mps_rank_weak()),
  "create ap");

 cdie(
  mps_ap_create(&apamc, poolamc, mps_rank_exact()),
  "create ap");

 formatcomments = 0;

 b = allocone(apamc, 1024, mps_rank_exact());

 c = mps_collections(arena);

 for (i=1; i<100; i++)
 {
  comment("%i of 100.", i);
  while (mps_collections(arena) == c) {
   a = allocone(apamc, 1024, mps_rank_exact());
   if (ranint(5)) {
    setref(a, 0, b);
   }
   b = a;
  }
  c = mps_collections(arena);
  a = allocone(apawl, 1, mps_rank_weak());
  a->data.id = 0;
  setref(a, 0, b);
 }

 mps_ap_destroy(apawl);
 mps_ap_destroy(apamc);
 comment("Destroyed aps.");

 mps_pool_destroy(poolamc);
 mps_pool_destroy(poolawl);
 comment("Destroyed pools.");

 mps_fmt_destroy(format);
 comment("Destroyed format.");

 mps_root_destroy(root);
 mps_root_destroy(rootb);
 comment("Destroyed roots.");

 mps_thread_dereg(thread);
 comment("Deregistered thread.");

 mps_arena_destroy(arena);
 comment("Destroyed arena.");

}

int main(void)
{
 void *m;
 stackpointer=&m; /* hack to get stack pointer */

 easy_tramp(test);
 pass();
 return 0;
}
