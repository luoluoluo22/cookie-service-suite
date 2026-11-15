package app

import (
	"context"
	"io"
	"net/http"
	"strings"
	"testing"
	"time"
)

// 面板改 request_timeout_sec 要立刻作用到新请求：缓存的客户端不能沿用旧超时。
func TestClientCacheFollowsTimeout(t *testing.T) {
	rtMu.Lock()
	saved := rtVal
	rtVal.RequestTimeout = 20
	rtMu.Unlock()
	defer func() { rtMu.Lock(); rtVal = saved; rtMu.Unlock() }()

	const proxy = "http://127.0.0.1:1"
	if got := getStdlibClient(proxy).Timeout; got != 20*time.Second {
		t.Fatalf("timeout = %v, want 20s", got)
	}
	if got := getStdlibStreamClient(proxy).Transport.(*http.Transport).ResponseHeaderTimeout; got != 20*time.Second {
		t.Fatalf("stream header timeout = %v, want 20s", got)
	}
	rtMu.Lock()
	rtVal.RequestTimeout = 180
	rtMu.Unlock()
	if got := getStdlibClient(proxy).Timeout; got != 180*time.Second {
		t.Fatalf("after change timeout = %v, want 180s", got)
	}
	if got := getStdlibStreamClient(proxy).Transport.(*http.Transport).ResponseHeaderTimeout; got != 180*time.Second {
		t.Fatalf("after change stream header timeout = %v, want 180s", got)
	}
	if getTLSClient() == nil {
		t.Fatal("tls client nil")
	}
}

func TestIdleTimeoutReadCloserAllowsActiveStream(t *testing.T) {
	pr, pw := io.Pipe()
	ctx, cancel := context.WithCancel(context.Background())
	wrapped := wrapIdleTimeoutReadCloser(pr, cancel, 120*time.Millisecond, 2*time.Second)
	defer wrapped.Close()

	go func() {
		defer pw.Close()
		for i := 0; i < 4; i++ {
			time.Sleep(50 * time.Millisecond)
			_, _ = pw.Write([]byte("chunk\n"))
		}
	}()

	data, err := io.ReadAll(wrapped)
	if err != nil {
		t.Fatalf("active stream unexpectedly failed: %v", err)
	}
	if ctx.Err() != nil && wrapped.reason.Load() != nil {
		t.Fatalf("unexpected cancel reason: %v", wrapped.reason.Load())
	}
	if strings.Count(string(data), "chunk") != 4 {
		t.Fatalf("got %q, want 4 chunks", string(data))
	}
}

func TestIdleTimeoutReadCloserStopsStalledStream(t *testing.T) {
	pr, pw := io.Pipe()
	defer pw.Close()

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		<-ctx.Done()
		_ = pr.Close()
	}()

	wrapped := wrapIdleTimeoutReadCloser(pr, cancel, 80*time.Millisecond, 2*time.Second)
	defer wrapped.Close()

	buf := make([]byte, 32)
	_, err := wrapped.Read(buf)
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "timeout") {
		t.Fatalf("stalled stream error = %v, want timeout error", err)
	}
}
