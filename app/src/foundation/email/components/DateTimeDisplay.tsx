import moment from "moment";

interface DateTimeDisplayProps {
  datetime?: string;
}

function DateTimeDisplay(props: DateTimeDisplayProps) {
  return (
    <>
      {
        moment(props.datetime).isSame(moment(), 'day') ?
        moment(props.datetime).format('LT') :
        moment(props.datetime).format('L')
      }
    </>
  )
}

export default DateTimeDisplay;