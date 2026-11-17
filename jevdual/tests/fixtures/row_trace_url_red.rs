
#[cfg(test)]
mod row_trace_url_review_tests {
    use super::*;
    #[test]
    fn invalid_trace_authorities_are_rejected() {
        for url in ["http://127.0.0.1:5176@outside.example/tasks", "http://user@127.0.0.1:5176/tasks",
            "http://127.0.0.1:5176/tasks?", "http://127.0.0.1:5176/tasks#", "http://127.0.0.1:0/tasks",
            "http://127.0.0.1:65536/tasks", "http://127.0.0.1:abc/tasks", "http://127.0.0.1:/tasks",
            "https://127.0.0.1:5176/tasks", "http://localhost:5176/tasks", "http://127.0.0.1.evil/tasks",
            "http://127.0.0.1:5176\\@outside.example/tasks", "http://127.0.0.1:5176/ta\nks"] {
            let typed: GetWindowStateInput = serde_json::from_value(serde_json::json!({
                "pid":77,"window_id":9,"qualify_rows":true,"row_trace_url":url})).unwrap();
            assert!(typed.validate().is_err(), "admitted {url:?}");
        }
    }
    #[test]
    fn exact_local_trace_and_no_trace_remain_valid() {
        for url in [None, Some("http://127.0.0.1:5176/tasks"), Some("http://127.0.0.1/tasks")] {
            let typed: GetWindowStateInput = serde_json::from_value(serde_json::json!({
                "pid":77,"window_id":9,"qualify_rows":true,"row_trace_url":url})).unwrap();
            assert!(typed.validate().is_ok());
        }
    }
}
