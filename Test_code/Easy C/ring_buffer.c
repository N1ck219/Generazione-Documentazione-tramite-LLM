#include "ring_buffer.h"
#include <stdlib.h>

rb_status_t rb_init(RingBuffer *rb, size_t capacity) {
    if (rb == NULL || capacity == 0) {
        return RB_ERR_NULL_PTR;
    }

    rb->data = (int *)malloc(capacity * sizeof(int));
    if (rb->data == NULL) {
        return RB_ERR_NO_MEM;
    }

    rb->capacity = capacity;
    rb->head = 0;
    rb->tail = 0;
    rb->count = 0;

    return RB_OK;
}

void rb_free(RingBuffer *rb) {
    if (rb != NULL && rb->data != NULL) {
        free(rb->data);
        rb->data = NULL;
        rb->capacity = 0;
        rb->head = 0;
        rb->tail = 0;
        rb->count = 0;
    }
}

rb_status_t rb_push(RingBuffer *rb, int value) {
    if (rb == NULL || rb->data == NULL) {
        return RB_ERR_NULL_PTR;
    }

    if (rb_is_full(rb)) {
        return RB_ERR_FULL;
    }

    rb->data[rb->head] = value;
    rb->head = (rb->head + 1) % rb->capacity;
    rb->count++;

    return RB_OK;
}

rb_status_t rb_pop(RingBuffer *rb, int *out_value) {
    if (rb == NULL || rb->data == NULL || out_value == NULL) {
        return RB_ERR_NULL_PTR;
    }

    if (rb_is_empty(rb)) {
        return RB_ERR_EMPTY;
    }

    *out_value = rb->data[rb->tail];
    rb->tail = (rb->tail + 1) % rb->capacity;
    rb->count--;

    return RB_OK;
}

bool rb_is_full(const RingBuffer *rb) {
    return (rb != NULL) && (rb->count == rb->capacity);
}

bool rb_is_empty(const RingBuffer *rb) {
    return (rb != NULL) && (rb->count == 0);
}

size_t rb_size(const RingBuffer *rb) {
    return (rb != NULL) ? rb->count : 0;
}