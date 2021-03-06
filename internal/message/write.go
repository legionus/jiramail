package message

import (
	"crypto/sha256"
	"fmt"
	"io"
	"net/textproto"
	"sort"
	"strings"
)

func writeMIMEHeader(w io.Writer, header textproto.MIMEHeader) (N int, err error) {
	var names sort.StringSlice
	var n int

	for name := range header {
		names = append(names, name)
	}

	names.Sort()

	for _, name := range names {
		for _, value := range header[name] {
			n, err = io.WriteString(w, name+": "+value+"\n")
			N += n
			if err != nil {
				return
			}
		}
	}

	n, err = io.WriteString(w, "\n")
	N += n
	return
}

func writeMessage(w io.Writer, header textproto.MIMEHeader, body io.Reader) error {
	if _, err := writeMIMEHeader(w, header); err != nil {
		return err
	}
	if _, err := io.Copy(w, body); err != nil {
		return err
	}
	return nil
}

func getBodyReader(m *Mail) io.Reader {
	var readers []io.Reader
	readers = append(readers, strings.NewReader(JiraStart+"\n# This block will be automatically deleted from the text.\n"))
	if m.Meta != nil && len(m.Meta.Data) > 0 {
		readers = append(
			readers,
			strings.NewReader("#\n"),
			strings.NewReader(m.Meta.WithPrefix("# ").String()),
			strings.NewReader("#\n"),
		)
	}
	readers = append(readers, strings.NewReader(JiraEnd+"\n\n"))
	for _, s := range m.Body {
		readers = append(readers, strings.NewReader(s+"\n"))
	}
	return io.MultiReader(readers...)
}

func MakeChecksum(m *Mail) (string, error) {
	hdr := make(textproto.MIMEHeader)
	for k, v := range m.Header {
		if k != "X-Checksum" {
			hdr[k] = v
		}
	}

	temp := &Mail{
		Rcpt:   m.Rcpt,
		Header: hdr,
		Body:   m.Body,
	}

	if m.Meta != nil {
		temp.Meta = m.Meta.Clone()
		temp.Meta.Headers = []string{JiraNewColumn}
		temp.Meta.ColumnWidth = 4096
	}

	h := sha256.New()

	err := writeMessage(h, temp.Header, getBodyReader(temp))
	if err != nil {
		return "", err
	}

	return fmt.Sprintf("sha256:%x", h.Sum(nil)), nil
}

func Write(w io.Writer, m *Mail, n int) error {
	if m.Meta != nil {
		m.Meta.Headers = []string{JiraPrevColumn, JiraDiffColumn, JiraNewColumn}
		m.Meta.ColumnWidth = n
	}
	return writeMessage(w, m.Header, getBodyReader(m))
}
