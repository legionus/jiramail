package message

import (
	"bufio"
	//"bytes"
	"fmt"
	"io"
	//"io/ioutil"
	"net/textproto"
	"os"
	"strings"

	"github.com/legionus/jiramail/internal/config"
	"github.com/legionus/jiramail/internal/message/meta"
)

const (
	JiraStart = "{{{ jira"
	JiraEnd   = "}}}"

	JiraNewColumn  = "Current"
	JiraPrevColumn = "Previous"
	JiraDiffColumn = "x"
)

type Meta struct {
	num  int
	Name map[string]int
	Data map[string]string
}

func (m *Meta) Set(k, v string) {
	if m.Name == nil {
		m.Name = make(map[string]int)
	}
	if m.Data == nil {
		m.Data = make(map[string]string)
	}
	m.Name[k] = m.num
	m.Data[k] = v
	m.num += 1
}

type Mail struct {
	Rcpt   *Address
	Header textproto.MIMEHeader
	Meta   *meta.Table
	Body   []string
}

func NewMail() *Mail {
	return &Mail{
		Header: make(textproto.MIMEHeader),
		Meta:   &meta.Table{},
	}
}

func (m *Mail) HeaderID() string {
	id := m.Header.Get("Message-ID")

	if strings.HasPrefix(id, "<") && strings.HasSuffix(id, ">") {
		return id[1 : len(id)-1]
	}

	if len(id) == 0 {
		panic(fmt.Sprintf("empty or not found header: Message-ID\n\n%#+v\n", m))
	}

	return id
}

func (m *Mail) HeaderChecksum() string {
	return m.Header.Get("X-Checksum")
}

func (m *Mail) GetBody() string {
	var x []string
	for _, s := range m.Body {
		if s == "\n" {
			s = ""
		}
		x = append(x, s)
	}
	return strings.TrimSpace(strings.Join(x, "\n"))
}

func ReadMail(cfg *config.Configuration, rd io.Reader) (msg *Mail, err error) {
	msg = NewMail()

	tp := textproto.NewReader(bufio.NewReader(rd))

	msg.Header, err = tp.ReadMIMEHeader()
	if err != nil {
		return nil, err
	}

	scanner := bufio.NewScanner(tp.R)

	metaparser := meta.NewParser()
	ismeta := false

	for scanner.Scan() {
		s := strings.TrimSpace(scanner.Text())
		switch {
		case s == JiraStart || strings.HasSuffix(s, " "+JiraStart):
			ismeta = true
		case s == JiraEnd || strings.HasSuffix(s, " "+JiraEnd):
			ismeta = false
		default:
			for _, quote := range cfg.Mail.MailQuote {
				s = strings.TrimPrefix(s, quote)
			}
			if ismeta {
				if !strings.HasPrefix(s, "#") {
					continue
				}
				s = strings.TrimPrefix(s, "#")

				if !metaparser.Scan(s) {
					if err = metaparser.Error(); err != nil {
						return nil, err
					}
				}
			} else if len(s) > 0 {
				msg.Body = append(msg.Body, s)
			}
		}
	}

	if err = scanner.Err(); err != nil {
		return nil, err
	}

	msg.Meta = metaparser.Table()

	if msg.Meta != nil {
		msg.Meta.ColumnWidth = cfg.Mail.JiraTableColumnWidth
	}

	return msg, nil
}

func ReadMailfile(cfg *config.Configuration, fp string) (*Mail, error) {
	fd, err := os.Open(fp)
	if err != nil {
		return nil, err
	}
	defer fd.Close()

	return ReadMail(cfg, fd)
}

func GetChecksum(cfg *config.Configuration, fp string) (string, error) {
	m, err := ReadMailfile(cfg, fp)
	if err != nil {
		return "", err
	}

	return m.HeaderChecksum(), nil
}
