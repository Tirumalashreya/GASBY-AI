#ffplay final_broadcast.mp4
curl -X POST http://127.0.0.1:5000/action-predict/predict \
-H "Content-Type: application/json" \
-d '{"uuid":"test-folder"}'
