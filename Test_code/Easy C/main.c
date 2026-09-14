#include <stdio.h>
#include "ring_buffer.h"

int main(void) {
    RingBuffer buffer;
    
    if (rb_init(&buffer, 3) != RB_OK) {
        fprintf(stderr, "Errore di allocazione del buffer\n");
        return 1;
    }

    /* Inserimento dati */
    rb_push(&buffer, 10);
    rb_push(&buffer, 20);
    rb_push(&buffer, 30);

    /* Test condizione buffer pieno */
    if (rb_push(&buffer, 40) == RB_ERR_FULL) {
        printf("Buffer pieno: elemento 40 rifiutato.\n");
    }

    /* Estrazione dati */
    int value = 0;
    while (!rb_is_empty(&buffer)) {
        rb_pop(&buffer, &value);
        printf("Estratto valore: %d\n", value);
    }

    rb_free(&buffer);
    return 0;
}