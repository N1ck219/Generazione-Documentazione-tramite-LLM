#ifndef RING_BUFFER_H
#define RING_BUFFER_H

#include <stddef.h>
#include <stdbool.h>

/**
 * Codici di stato restituiti dalle operazioni sul buffer.
 */
typedef enum {
    RB_OK = 0,
    RB_ERR_NULL_PTR = -1,
    RB_ERR_FULL = -2,
    RB_ERR_EMPTY = -3,
    RB_ERR_NO_MEM = -4
} rb_status_t;

/**
 * Struttura principale del buffer circolare.
 */
typedef struct {
    int *data;
    size_t capacity;
    size_t head;
    size_t tail;
    size_t count;
} RingBuffer;

/* Inizializzazione e deallocazione */
rb_status_t rb_init(RingBuffer *rb, size_t capacity);
void rb_free(RingBuffer *rb);

/* Operazioni di lettura e scrittura */
rb_status_t rb_push(RingBuffer *rb, int value);
rb_status_t rb_pop(RingBuffer *rb, int *out_value);

/* Query sullo stato */
bool rb_is_full(const RingBuffer *rb);
bool rb_is_empty(const RingBuffer *rb);
size_t rb_size(const RingBuffer *rb);

#endif /* RING_BUFFER_H */