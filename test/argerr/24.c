/* 
TEST_HEADER
 id = $Id$
 summary = zero 3rd arg to mps_alloc (MFS)
 language = c
 link = testlib.o
OUTPUT_SPEC
 assert = true
 assertfile P= mpsi.c
 assertcond = size > 0
END_HEADER
*/

#include "testlib.h"
#include "mpscmfs.h"
#include "arg.h"

static void test(void *stack_pointer)
{
 mps_arena_t arena;
 mps_pool_t pool;
 mps_thr_t thread;

 size_t mysize;
 mps_addr_t a;

 cdie(mps_arena_create(&arena, mps_arena_class_vm(), mmqaArenaSIZE), "create arena");

 cdie(mps_thread_reg(&thread, arena), "register thread");

 mysize = 8;

 cdie(
  mps_pool_create(
     &pool, arena, mps_class_mfs(), (size_t) 8, mysize),
  "create pool");

 mps_alloc(&a, pool, 0);
 mps_pool_destroy(pool);

}

int main(void)
{
 run_test(test);
 return 0;
}
