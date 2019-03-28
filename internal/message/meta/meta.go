package meta

import (
	"fmt"
	"io"
	"strings"
)

const (
	Delim       = "|"
	ColumnWidth = 40
)

type Field struct {
	Name   string
	Column map[string]string
}

type Table struct {
	prefix      string
	ColumnWidth int
	Headers     []string
	Data        []Field
}

func (t *Table) Clone() *Table {
	return &Table{
		prefix:      t.prefix,
		ColumnWidth: t.ColumnWidth,
		Headers:     t.Headers,
		Data:        t.Data,
	}
}

func (t *Table) WithPrefix(v string) *Table {
	return &Table{
		prefix:      v,
		ColumnWidth: t.ColumnWidth,
		Headers:     t.Headers,
		Data:        t.Data,
	}
}

func (t *Table) Append(nfield Field) {
	for _, field := range t.Data {
		if field.Name == nfield.Name {
			return
		}
	}

	x := map[string]struct{}{}

	for _, n := range t.Headers {
		x[n] = struct{}{}
	}

	for k := range nfield.Column {
		if _, ok := x[k]; !ok {
			t.Headers = append(t.Headers, k)
		}
	}

	t.Data = append(t.Data, nfield)
}

func (t *Table) SetColumns(name string, columns map[string]string) {
	for _, field := range t.Data {
		if field.Name != name {
			continue
		}
		for k := range columns {
			field.Column[k] = columns[k]
		}
		return
	}
	t.Append(Field{
		Name:   name,
		Column: columns,
	})
}

func (t *Table) Set(name string, column string, value string) {
	t.SetColumns(name, map[string]string{
		column: value,
	})
}

func (t *Table) Get(name, colname string) string {
	for _, field := range t.Data {
		if field.Name == name {
			for k, v := range field.Column {
				if k == colname {
					return v
				}
			}
		}
	}
	return ""
}

func (t Table) Write(w io.Writer) {
	lenName := 0
	lenColumns := make(map[string]int)

	for _, field := range t.Data {
		if lenName < len(field.Name) {
			lenName = len(field.Name)
		}
		for name, data := range field.Column {
			if lenColumns[name] < len(data) {
				if len(data) > t.ColumnWidth {
					lenColumns[name] = t.ColumnWidth
				} else {
					lenColumns[name] = len(data)
				}
			}
		}
	}

	for _, name := range t.Headers {
		n, ok := lenColumns[name]
		if !ok || n == 0 {
			continue
		}
		if n < len(name) {
			lenColumns[name] = len(name)
		}
	}

	header := fmt.Sprintf(fmt.Sprintf("%%-%ds", lenName), "Name")
	for _, name := range t.Headers {
		n, ok := lenColumns[name]
		if !ok || n == 0 {
			continue
		}
		header += fmt.Sprintf(fmt.Sprintf(" %s %%-%ds", Delim, n), name)
	}

	w.Write([]byte(t.prefix + header + "\n"))
	w.Write([]byte(t.prefix + strings.Repeat("-", len(header)) + "\n"))

	var moreField *Field

	for _, field := range t.Data {
	LABEL:
		s := fmt.Sprintf(fmt.Sprintf("%%-%ds", lenName), field.Name)
		for _, name := range t.Headers {
			n, ok := lenColumns[name]
			if !ok || n == 0 {
				continue
			}

			eol := len(field.Column[name])
			if eol > t.ColumnWidth {
				eol = t.ColumnWidth

				if moreField == nil {
					moreField = &Field{
						Name:   "",
						Column: map[string]string{},
					}
				}

				moreField.Column[name] = field.Column[name][eol:]
			}

			format := fmt.Sprintf("%%-%ds", n)
			data := fmt.Sprintf(format, field.Column[name][0:eol])

			s += fmt.Sprintf(" %s %s", Delim, data)
		}

		w.Write([]byte(t.prefix + s + "\n"))

		if moreField != nil {
			field = *moreField
			moreField = nil
			goto LABEL
		}
	}

	w.Write([]byte(t.prefix + strings.Repeat("-", len(header)) + "\n"))
}

func (t Table) String() string {
	wr := &strings.Builder{}
	t.Write(wr)
	return wr.String()
}

type Parser struct {
	lines     int
	err       error
	closed    bool
	headers   []string
	table     *Table
	lastfield *Field
}

func NewParser() *Parser {
	return &Parser{}
}

func (p *Parser) Scan(s string) bool {
	if p.closed {
		return false
	}

	s = strings.TrimSpace(s)

	if len(s) == 0 {
		return true
	}

	p.lines += 1

	switch p.lines {
	case 1:
		if !strings.ContainsAny(s, Delim) {
			p.lines = 0
			return true
		}

		a := strings.SplitN(s, Delim, -1)

		for i, v := range a {
			if i > 0 {
				v = strings.TrimSpace(v)
				if len(v) == 0 {
					v = fmt.Sprintf("%d", i)
				}
				p.headers = append(p.headers, v)
			}
		}
		p.table = &Table{
			ColumnWidth: ColumnWidth,
			Headers:     p.headers,
		}
	case 2:
		if x := strings.Replace(s, "-", "", -1); len(x) != 0 {
			p.err = fmt.Errorf("Unexpected header (line=%d)", p.lines)
			p.closed = true
		}
	default:
		if x := strings.Replace(s, "-", "", -1); len(x) == 0 {
			p.closed = true
			return false
		}

		if !strings.ContainsAny(s, Delim) {
			p.err = fmt.Errorf("Unexpected line format (line=%d)", p.lines)
			p.closed = true
			return false
		}

		a := strings.SplitN(s, Delim, -1)

		f := &Field{
			Name:   strings.TrimSpace(a[0]),
			Column: make(map[string]string, len(p.headers)),
		}

		for _, n := range p.headers {
			f.Column[n] = ""
		}

		for i := range a[1:] {
			if i >= len(p.headers) {
				break
			}
			f.Column[p.headers[i]] = strings.TrimSpace(a[i+1])
		}

		if f.Name == "" {
			for _, n := range p.headers {
				if len(f.Column[n]) > 0 {
					p.lastfield.Column[n] += f.Column[n]
				}
			}
		} else {
			p.table.Append(*f)
			p.lastfield = f
		}
	}

	return true
}

func (p *Parser) Error() error {
	return p.err
}

func (p *Parser) Table() *Table {
	return p.table
}
