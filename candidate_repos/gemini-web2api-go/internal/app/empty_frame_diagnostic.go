package app

import (
	"encoding/json"
	"strings"
)

// emptyFrameDiagnostic preserves protocol structure and short numeric codes only.
// Never write arbitrary strings, long identifiers, headers, or raw responses to logs.
func emptyFrameDiagnostic(raw []byte) string {
	if len(raw) > 16384 {
		return "[response too large to inspect]"
	}
	frames := make([]interface{}, 0)
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if !strings.HasPrefix(line, "[") && !strings.HasPrefix(line, "{") {
			continue
		}
		var value interface{}
		if json.Unmarshal([]byte(line), &value) == nil {
			frames = append(frames, redactDiagnostic(value))
		}
	}
	result, err := json.Marshal(frames)
	if err != nil {
		return "[unavailable]"
	}
	return string(result)
}

func redactDiagnostic(v interface{}) interface{} {
	switch x := v.(type) {
	case string:
		switch x {
		case "wrb.fr", "di", "af.httprm", "e", "type.googleapis.com/assistant.boq.bard.application.BardErrorInfo":
			return x
		default:
			return "[redacted]"
		}
	case float64:
		if x >= -9999 && x <= 9999 {
			return x
		}
		return "[number redacted]"
	case []interface{}:
		for i := range x {
			x[i] = redactDiagnostic(x[i])
		}
		return x
	case map[string]interface{}:
		// Object keys may contain private data, too; preserve values without keys.
		values := make([]interface{}, 0, len(x))
		for _, value := range x {
			values = append(values, redactDiagnostic(value))
		}
		return values
	default:
		return x
	}
}
