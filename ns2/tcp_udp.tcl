# NS-2.35 TCP Reno (FTP) vs UDP (CBR) over a shared bottleneck.
# Usage: ns ns2/tcp_udp.tcl LOSS_PERCENT DELAY_MS QUEUE_PACKETS OUTPUT_PREFIX SEED
if {$argc != 5} {
    puts stderr "Usage: ns tcp_udp.tcl LOSS_PERCENT DELAY_MS QUEUE_PACKETS OUTPUT_PREFIX SEED"
    exit 2
}
set loss_percent [lindex $argv 0]
set delay_ms [lindex $argv 1]
set queue_packets [lindex $argv 2]
set prefix [lindex $argv 3]
set seed [lindex $argv 4]
if {![string is double -strict $loss_percent] || $loss_percent < 0 || $loss_percent > 100} {error "Loss must be 0..100"}
if {![string is double -strict $delay_ms] || $delay_ms < 0 || $delay_ms > 2000} {error "Delay must be 0..2000"}
if {![string is integer -strict $queue_packets] || $queue_packets < 1 || $queue_packets > 10000} {error "Queue must be 1..10000"}
if {![string is integer -strict $seed]} {error "Seed must be an integer"}
ns-random $seed
set ns [new Simulator]
set tr [open "${prefix}.tr" w]
$ns trace-all $tr
set nf [open "${prefix}.nam" w]
$ns namtrace-all $nf
set tcp_src [$ns node]; set udp_src [$ns node]
set r1 [$ns node]; set r2 [$ns node]
set tcp_dst [$ns node]; set udp_dst [$ns node]
$ns duplex-link $tcp_src $r1 10Mb 5ms DropTail
$ns duplex-link $udp_src $r1 10Mb 5ms DropTail
$ns duplex-link $r1 $r2 1Mb ${delay_ms}ms DropTail
$ns duplex-link $r2 $tcp_dst 10Mb 5ms DropTail
$ns duplex-link $r2 $udp_dst 10Mb 5ms DropTail
$ns queue-limit $r1 $r2 $queue_packets
$ns queue-limit $r2 $r1 $queue_packets
if {$loss_percent > 0} {
    set em [new ErrorModel]
    $em set rate_ [expr {$loss_percent / 100.0}]
    $em unit pkt
    $em ranvar [new RandomVariable/Uniform]
    $ns lossmodel $em $r1 $r2
}
set tcp [new Agent/TCP/Reno]
$tcp set fid_ 1
$tcp set packetSize_ 1000
$ns attach-agent $tcp_src $tcp
set sink [new Agent/TCPSink]
$ns attach-agent $tcp_dst $sink
$ns connect $tcp $sink
set ftp [new Application/FTP]
$ftp attach-agent $tcp
set udp [new Agent/UDP]
$udp set fid_ 2
$udp set packetSize_ 1000
$ns attach-agent $udp_src $udp
set null [new Agent/Null]
$ns attach-agent $udp_dst $null
$ns connect $udp $null
set cbr [new Application/Traffic/CBR]
$cbr set packetSize_ 1000
$cbr set interval_ 0.02
$cbr set random_ false
$cbr attach-agent $udp
$ns at 1.0 "$ftp start"
$ns at 1.0 "$cbr start"
$ns at 12.0 "$ftp stop"
$ns at 12.0 "$cbr stop"
proc finish {} {
    global ns tr nf prefix loss_percent delay_ms
    $ns flush-trace
    close $tr
    close $nf
    puts "Completed: ${prefix}.tr | loss=${loss_percent}% delay=${delay_ms}ms"
    exit 0
}
$ns at 14.0 "finish"
$ns run
