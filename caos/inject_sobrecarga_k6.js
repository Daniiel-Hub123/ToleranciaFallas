import http from 'k6/http';
import { sleep } from 'k6';

// Configuración de la prueba de carga: 15 usuarios concurrentes por 10 segundos
export const options = {
    vus: 15,
    duration: '10s',
};

// URL del API Gateway por defecto usando el NodePort 30088. 
// Puede ser sobreescrita pasando una variable de entorno: -e TARGET_URL=http://...
const url = __ENV.TARGET_URL || 'http://localhost:30088/reservar';

export default function () {
    const payload = JSON.stringify({
        asiento_id: 'asiento_1'
    });

    const params = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // Realizar la petición POST de reserva
    http.post(url, payload, params);
    
    // Pequeña pausa entre peticiones para regular el flujo por usuario virtual
    sleep(0.1); 
}
