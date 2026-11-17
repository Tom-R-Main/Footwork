#[cfg(test)]
mod row_trace_tests {
    use super::*;
    #[test]
    fn row_trace_typed_fields_survive_wire() {
        let request = serde_json::json!({"pid":77,"window_id":9,"qualify_rows":true,"row_trace_url":"http://127.0.0.1:5176/tasks"});
        let typed: GetWindowStateInput = serde_json::from_value(request.clone()).unwrap();
        assert_eq!(serde_json::to_value(typed).unwrap()["row_trace_url"], request["row_trace_url"]);
        let reply = serde_json::json!({"pid":77,"window_id":9,"row_trace_json":"{\"status\":\"capture_refused\"}"});
        let typed: WindowStateOutput = serde_json::from_value(reply.clone()).unwrap();
        assert_eq!(serde_json::to_value(typed).unwrap()["row_trace_json"],reply["row_trace_json"]);
    }
}
