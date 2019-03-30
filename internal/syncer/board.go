package syncer

import (
	"fmt"
	"os"
	"regexp"

	"github.com/andygrunwald/go-jira"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/jiraplus"
)

func (s *JiraSyncer) Boards() error {
	if s.config.Mail.Path.Board == "" {
		return nil
	}

	var (
		re *regexp.Regexp
	)

	if len(s.config.Remote[s.remote].ProjectMatch) > 0 {
		re = regexp.MustCompile(s.config.Remote[s.remote].BoardMatch)
	}

	refs := []string{jiraconv.RemoteMessageID(s.remote)}

	opts := &jira.BoardListOptions{}
	opts.MaxResults = 100

	handled := 0
	count, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.Board.GetAllBoards(opts)
			if err != nil {
				return nil, fmt.Errorf("unable to get boards: %s", err)
			}

			a := make([]interface{}, len(ret.Values))

			for k := range ret.Values {
				a[k] = &ret.Values[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			board := o.(*jira.Board)

			if board.Type != "scrum" {
				return nil
			}

			if re != nil {
				if !re.MatchString(board.Name) {
					return nil
				}
			}

			s.vars["BoardName"] = ReplaceStringTrash(board.Name)
			s.vars["BoardID"] = fmt.Sprintf("%d", board.ID)

			mdir := s.getPath(s.config.Mail.Path.Board)

			err := os.MkdirAll(mdir, 0755)
			if err != nil {
				return err
			}

			err = s.sprints(board, refs)
			if err != nil {
				return err
			}

			err = s.epics(board, refs)
			if err != nil {
				return err
			}

			err = s.backlog(board, refs)
			if err != nil {
				return err
			}

			handled += 1
			return nil
		},
	)

	delete(s.vars, "BoardName")
	delete(s.vars, "BoardID")

	if err != nil {
		return err
	}

	logrus.Infof("remote %q, %d boards were found and %d handled", s.remote, count, handled)

	return nil
}
