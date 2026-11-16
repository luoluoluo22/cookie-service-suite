package app

import (
	"strings"
	"testing"
)

func TestEmptyFrameDiagnosticRedactsPrivateData(t *testing.T) {
	raw := `)]}'` + "\n" + `[["wrb.fr",null,"private prompt",["type.googleapis.com/assistant.boq.bard.application.BardErrorInfo",[1155]],123456789,"secret-cookie"]]`
	got := emptyFrameDiagnostic([]byte(raw))
	for _, secret := range []string{"private prompt", "secret-cookie", "123456789"} {
		if strings.Contains(got, secret) {
			t.Fatalf("diagnostic leaked %q: %s", secret, got)
		}
	}
	if !strings.Contains(got, "1155") || !strings.Contains(got, "BardErrorInfo") {
		t.Fatalf("missing diagnostic code: %s", got)
	}
}
