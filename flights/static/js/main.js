document.addEventListener('DOMContentLoaded', () => {
    // 1. Obtener referencias a los elementos clave del carrusel
    const carouselWrapper = document.querySelector('.carousel-wrapper');
    if (!carouselWrapper) return; // Salir si la sección no existe

    const container = carouselWrapper.querySelector('.carousel-container');
    const track = carouselWrapper.querySelector('.carousel-track');
    const leftArrow = carouselWrapper.querySelector('.left-arrow');
    const rightArrow = carouselWrapper.querySelector('.right-arrow');

    // Comprobación de existencia (necesaria si se navega a otras páginas)
    if (!container || !track || !leftArrow || !rightArrow) {
        return;
    }

    // Obtener el ancho de una tarjeta y el espacio (gap)
    const firstCard = track.querySelector('.package-card');
    if (!firstCard) return; 

    // OffsetWidth incluye padding y border.
    const cardWidth = firstCard.offsetWidth;
    const gap = 20; // Asegúrate de que este valor coincida con el CSS 'gap'
    const cardsToShow = 4;
    
    // 2. Calcular la cantidad de píxeles a desplazar (4 tarjetas + 3 espacios entre ellas)
    const scrollAmount = (cardWidth * cardsToShow) + (gap * (cardsToShow - 1));

    // 3. Función para actualizar la visibilidad de las flechas
    // Muestra/Oculta flechas al inicio/final del carrusel.
    const updateArrows = () => {
        const maxScrollLeft = container.scrollWidth - container.clientWidth;
        const currentScroll = container.scrollLeft;

        // Flecha izquierda: Ocultar al inicio
        leftArrow.style.display = currentScroll > 0 ? 'flex' : 'none';
        
        // Flecha derecha: Ocultar al final (Usamos -1 para compensar posibles errores de redondeo)
        rightArrow.style.display = currentScroll < maxScrollLeft - 1 ? 'flex' : 'none';
    };

    // 4. Evento para flecha Derecha (Siguiente)
    rightArrow.addEventListener('click', () => {
        container.scrollBy({
            left: scrollAmount,
            behavior: 'smooth'
        });
    });

    // 5. Evento para flecha Izquierda (Anterior)
    leftArrow.addEventListener('click', () => {
        container.scrollBy({
            left: -scrollAmount,
            behavior: 'smooth'
        });
    });

    // 6. Listener para actualizar las flechas mientras el usuario hace scroll
    container.addEventListener('scroll', updateArrows);

    // 7. Inicializar la visibilidad de las flechas (La flecha izquierda debe estar oculta al inicio)
    // Usamos setTimeout para asegurar que todas las dimensiones CSS se hayan aplicado.
    setTimeout(updateArrows, 100);

});